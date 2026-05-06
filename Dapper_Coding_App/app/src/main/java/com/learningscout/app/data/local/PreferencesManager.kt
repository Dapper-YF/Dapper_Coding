package com.learningscout.app.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.*
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import java.util.UUID

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "settings")

class PreferencesManager(private val context: Context) {
    private val authTokenKey = stringPreferencesKey("auth_token")
    private val darkModeKey = booleanPreferencesKey("dark_mode")
    private val onboardingCompleteKey = booleanPreferencesKey("onboarding_complete")
    private val deviceIdKey = stringPreferencesKey("device_id")
    private val defaultConversationIdKey = stringPreferencesKey("default_conversation_id")
    private val skipVersionKey = intPreferencesKey("skip_version")

    suspend fun getSkipVersion(): Int = context.dataStore.data.first()[skipVersionKey] ?: 0

    suspend fun setSkipVersion(version: Int) {
        context.dataStore.edit { it[skipVersionKey] = version }
    }

    suspend fun getAuthToken(): String? = context.dataStore.data.first()[authTokenKey]

    suspend fun saveAuthToken(token: String) {
        context.dataStore.edit { it[authTokenKey] = token }
    }

    suspend fun clearAuthToken() {
        context.dataStore.edit { it.remove(authTokenKey) }
    }

    suspend fun isDarkMode(): Boolean = context.dataStore.data.first()[darkModeKey] ?: false

    suspend fun setDarkMode(enabled: Boolean) {
        context.dataStore.edit { it[darkModeKey] = enabled }
    }

    suspend fun isOnboardingComplete(): Boolean =
        context.dataStore.data.first()[onboardingCompleteKey] ?: false

    suspend fun setOnboardingComplete() {
        context.dataStore.edit { it[onboardingCompleteKey] = true }
    }

    suspend fun getDeviceId(): String {
        val existing = context.dataStore.data.first()[deviceIdKey]
        if (existing != null) return existing
        val newId = UUID.randomUUID().toString()
        context.dataStore.edit { it[deviceIdKey] = newId }
        return newId
    }

    suspend fun getDefaultConversationId(): String {
        val existing = context.dataStore.data.first()[defaultConversationIdKey]
        if (existing != null) return existing
        val newId = UUID.randomUUID().toString().take(8)
        context.dataStore.edit { it[defaultConversationIdKey] = newId }
        return newId
    }
}
