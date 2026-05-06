package com.learningscout.app.data.remote

import com.learningscout.app.data.local.PreferencesManager
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject

class TokenExpiryInterceptor @Inject constructor(
    private val preferencesManager: PreferencesManager,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val response = chain.proceed(chain.request())
        if (response.code == 401) {
            runBlocking { preferencesManager.clearAuthToken() }
            AuthEventBus.onTokenExpired()
        }
        return response
    }
}
