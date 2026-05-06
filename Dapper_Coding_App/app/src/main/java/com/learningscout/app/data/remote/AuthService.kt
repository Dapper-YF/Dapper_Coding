package com.learningscout.app.data.remote

import com.learningscout.app.data.remote.dto.AppVersionResponse
import com.learningscout.app.data.remote.dto.AuthResponse
import com.learningscout.app.data.remote.dto.CompleteOnboardingRequest
import com.learningscout.app.data.remote.dto.CompleteOnboardingResponse
import com.learningscout.app.data.remote.dto.LoginEmailRequest
import com.learningscout.app.data.remote.dto.LoginRequest
import com.learningscout.app.data.remote.dto.OnboardingStatusResponse
import com.learningscout.app.data.remote.dto.OnboardingTreeResponse
import com.learningscout.app.data.remote.dto.ProfileResponse
import com.learningscout.app.data.remote.dto.RegisterEmailRequest
import com.learningscout.app.data.remote.dto.RegisterRequest
import com.learningscout.app.data.remote.dto.UpdateProfileRequest
import com.learningscout.app.data.remote.dto.UpdateProfileResponse
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT

interface AuthService {
    @POST("api/auth/register")
    suspend fun register(@Body request: RegisterRequest): Response<AuthResponse>

    @POST("api/auth/login")
    suspend fun login(@Body request: LoginRequest): Response<AuthResponse>

    @POST("api/auth/register-email")
    suspend fun registerEmail(@Body request: RegisterEmailRequest): Response<AuthResponse>

    @POST("api/auth/login-email")
    suspend fun loginEmail(@Body request: LoginEmailRequest): Response<AuthResponse>

    @GET("api/onboarding/tree")
    suspend fun getOnboardingTree(
        @Header("Authorization") authorization: String,
    ): Response<OnboardingTreeResponse>

    @POST("api/onboarding/complete")
    suspend fun completeOnboarding(
        @Header("Authorization") authorization: String,
        @Body request: CompleteOnboardingRequest,
    ): Response<CompleteOnboardingResponse>

    @GET("api/user/onboarding-status")
    suspend fun getOnboardingStatus(
        @Header("Authorization") authorization: String,
    ): Response<OnboardingStatusResponse>

    @GET("api/user/profile")
    suspend fun getProfile(
        @Header("Authorization") authorization: String,
    ): Response<ProfileResponse>

    @PUT("api/user/profile")
    suspend fun updateProfile(
        @Header("Authorization") authorization: String,
        @Body request: UpdateProfileRequest,
    ): Response<UpdateProfileResponse>

    @GET("api/app/version")
    suspend fun getAppVersion(): Response<AppVersionResponse>
}
