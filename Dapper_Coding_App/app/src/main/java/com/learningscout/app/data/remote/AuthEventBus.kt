package com.learningscout.app.data.remote

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

object AuthEventBus {
    private val _tokenExpired = MutableStateFlow(0L)
    val tokenExpired: StateFlow<Long> = _tokenExpired.asStateFlow()

    fun onTokenExpired() {
        _tokenExpired.value = System.currentTimeMillis()
    }
}
