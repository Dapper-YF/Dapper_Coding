package com.learningscout.app.ui.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import com.learningscout.app.data.local.PreferencesManager
import com.learningscout.app.data.remote.dto.AppVersionResponse
import com.learningscout.app.data.remote.AuthEventBus
import com.learningscout.app.data.remote.AuthService
import com.learningscout.app.data.remote.UpdateChecker
import com.learningscout.app.di.AuthServiceEntryPoint
import com.learningscout.app.ui.components.BottomNavTab
import com.learningscout.app.ui.components.LearningScoutBottomNavBar
import com.learningscout.app.ui.components.LearningScoutTopAppBar
import com.learningscout.app.ui.components.UpdateDialog
import com.learningscout.app.ui.screens.auth.LoginScreen
import com.learningscout.app.ui.screens.auth.RegisterScreen
import com.learningscout.app.ui.screens.chat.ChatScreen
import com.learningscout.app.ui.screens.chat.ChatViewModel
import com.learningscout.app.ui.screens.learn.LearnScreen
import com.learningscout.app.ui.screens.learn.LearnViewModel
import com.learningscout.app.ui.screens.onboarding.OnboardingScreen
import com.learningscout.app.ui.screens.profile.ProfileScreen
import com.learningscout.app.ui.screens.profile.ProfileViewModel
import com.learningscout.app.ui.theme.LearningScoutTheme
import androidx.hilt.navigation.compose.hiltViewModel
import dagger.hilt.android.EntryPointAccessors
import kotlinx.coroutines.launch

private enum class StartupDest {
    Loading, Login, Onboarding, Main
}

@Composable
fun MainNavigation() {
    val context = LocalContext.current
    val preferencesManager = remember { PreferencesManager(context) }
    val authService = remember {
        EntryPointAccessors.fromApplication(
            context.applicationContext,
            AuthServiceEntryPoint::class.java,
        ).authService()
    }

    var destination by remember { mutableStateOf(StartupDest.Loading) }
    var isRegistering by remember { mutableStateOf(false) }
    var isDarkMode by remember { mutableStateOf(false) }
    var updateInfo by remember { mutableStateOf<AppVersionResponse?>(null) }
    val scope = rememberCoroutineScope()

    var defaultConversationId by remember { mutableStateOf("default") }

    LaunchedEffect(Unit) {
        isDarkMode = preferencesManager.isDarkMode()
        defaultConversationId = preferencesManager.getDefaultConversationId()

        val serverVersion = UpdateChecker.checkForUpdate()
        if (serverVersion != null && UpdateChecker.hasUpdate(serverVersion)) {
            val skipVersion = preferencesManager.getSkipVersion()
            if (serverVersion.version > skipVersion) {
                updateInfo = serverVersion
            }
        }

        val token = preferencesManager.getAuthToken()
        destination = if (token.isNullOrBlank()) {
            StartupDest.Login
        } else {
            val serverOnboarded = fetchOnboardingStatus(authService, token)
            if (serverOnboarded != null) {
                if (serverOnboarded) {
                    preferencesManager.setOnboardingComplete()
                }
                if (serverOnboarded) StartupDest.Main else StartupDest.Onboarding
            } else {
                val localOnboarded = preferencesManager.isOnboardingComplete()
                if (localOnboarded) StartupDest.Main else StartupDest.Onboarding
            }
        }
    }

    val expireTimestamp by AuthEventBus.tokenExpired.collectAsState(0L)
    LaunchedEffect(expireTimestamp) {
        if (expireTimestamp > 0L) {
            isRegistering = false
            destination = StartupDest.Login
        }
    }

    LearningScoutTheme(darkTheme = isDarkMode) {
        val update = updateInfo
        if (update != null) {
            UpdateDialog(
                versionName = update.versionName,
                changelog = update.changelog,
                forceUpdate = update.forceUpdate,
                onUpdate = {
                    UpdateChecker.downloadAndInstall(context, update.downloadUrl)
                    if (!update.forceUpdate) updateInfo = null
                },
                onDismiss = {
                    scope.launch { preferencesManager.setSkipVersion(update.version) }
                    updateInfo = null
                },
            )
        }

        when (destination) {
            StartupDest.Loading -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    CircularProgressIndicator()
                }
            }
            StartupDest.Login -> {
                if (isRegistering) {
                    RegisterScreen(
                        onRegisterSuccess = {
                            destination = StartupDest.Onboarding
                        },
                        onNavigateToLogin = {
                            isRegistering = false
                        },
                    )
                } else {
                    LoginScreen(
                        onLoginSuccess = {
                            scope.launch {
                                destination = if (preferencesManager.isOnboardingComplete()) {
                                    StartupDest.Main
                                } else {
                                    StartupDest.Onboarding
                                }
                            }
                        },
                        onNavigateToRegister = {
                            isRegistering = true
                        },
                    )
                }
            }
            StartupDest.Onboarding -> {
                OnboardingScreen(onComplete = { destination = StartupDest.Main })
            }
            StartupDest.Main -> {
                MainAppContent(
                    isDarkMode = isDarkMode,
                    onToggleDarkMode = {
                        isDarkMode = !isDarkMode
                        scope.launch {
                            preferencesManager.setDarkMode(isDarkMode)
                        }
                    },
                    onLogout = {
                        destination = StartupDest.Login
                    },
                    defaultConversationId = defaultConversationId,
                )
            }
        }
    }
}

@Composable
private fun MainAppContent(
    isDarkMode: Boolean,
    onToggleDarkMode: () -> Unit,
    onLogout: () -> Unit = {},
    defaultConversationId: String = "default",
) {
    var selectedTab by rememberSaveable { mutableStateOf(BottomNavTab.LEARN) }
    val snackbarHostState = remember { SnackbarHostState() }

    val learnViewModel: LearnViewModel = hiltViewModel()
    val chatViewModel: ChatViewModel = hiltViewModel()
    val profileViewModel: ProfileViewModel = hiltViewModel()

    LaunchedEffect(selectedTab) {
        when (selectedTab) {
            BottomNavTab.LEARN -> learnViewModel.refresh()
            BottomNavTab.CHAT -> chatViewModel.refresh()
            BottomNavTab.PROFILE -> profileViewModel.refresh()
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = MaterialTheme.colorScheme.background,
    ) {
        Scaffold(
            snackbarHost = { SnackbarHost(snackbarHostState) },
            topBar = {
                LearningScoutTopAppBar(
                    onDarkModeToggle = onToggleDarkMode,
                    onRefreshClick = {
                        when (selectedTab) {
                            BottomNavTab.LEARN -> learnViewModel.refresh()
                            BottomNavTab.CHAT -> chatViewModel.refresh()
                            BottomNavTab.PROFILE -> profileViewModel.refresh()
                        }
                    },
                )
            },
            bottomBar = {
                LearningScoutBottomNavBar(
                    selectedTab = selectedTab,
                    onTabSelected = { selectedTab = it },
                )
            },
        ) { innerPadding ->
            val modifier = Modifier.padding(innerPadding)
            when (selectedTab) {
                BottomNavTab.LEARN -> LearnScreen(
                    modifier = modifier,
                    viewModel = learnViewModel,
                )
                BottomNavTab.CHAT -> ChatScreen(
                    modifier = modifier,
                    viewModel = chatViewModel,
                    conversationId = defaultConversationId,
                )
                BottomNavTab.PROFILE -> ProfileScreen(
                    modifier = modifier,
                    viewModel = profileViewModel,
                    isDarkMode = isDarkMode,
                    onToggleDarkMode = onToggleDarkMode,
                    onLogout = onLogout,
                )
            }
        }
    }
}

private suspend fun fetchOnboardingStatus(
    authService: AuthService,
    token: String,
): Boolean? {
    return try {
        val response = authService.getOnboardingStatus("Bearer $token")
        if (response.isSuccessful) response.body()?.onboarding_complete else null
    } catch (_: Exception) {
        null
    }
}
