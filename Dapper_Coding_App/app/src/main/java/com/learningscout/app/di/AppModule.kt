package com.learningscout.app.di

import android.content.Context
import androidx.room.Room
import com.learningscout.app.BuildConfig
import com.learningscout.app.data.local.AppDatabase
import com.learningscout.app.data.local.PreferencesManager
import com.learningscout.app.data.local.dao.ChatDao
import com.learningscout.app.data.remote.ApiService
import com.learningscout.app.data.remote.AuthService
import com.learningscout.app.data.remote.RetrofitClient
import com.learningscout.app.data.remote.TokenExpiryInterceptor
import dagger.Module
import dagger.Provides
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit
import javax.inject.Named
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object AppModule {

    @Provides
    @Singleton
    fun provideDatabase(@ApplicationContext context: Context): AppDatabase {
        return Room.databaseBuilder(
            context,
            AppDatabase::class.java,
            "learning_scout.db"
        ).addMigrations(AppDatabase.MIGRATION_2_3)
         .fallbackToDestructiveMigration()
         .build()
    }

    @Provides
    fun provideChatDao(database: AppDatabase): ChatDao {
        return database.chatDao()
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(): OkHttpClient {
        return RetrofitClient.okHttpClient
    }

    @Provides
    @Singleton
    @Named("apiClient")
    fun provideApiOkHttpClient(
        tokenExpiryInterceptor: TokenExpiryInterceptor,
    ): OkHttpClient {
        // Build from scratch — do NOT copy the base OkHttpClient because its
        // HttpLoggingInterceptor(Level.BODY) buffers the entire response body,
        // which blocks SSE streaming (onDelta/onComplete never fire).
        return OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(35, TimeUnit.SECONDS)
            .addInterceptor(tokenExpiryInterceptor)
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                    .addHeader("Authorization", "Bearer ${BuildConfig.API_TOKEN}")
                    .build()
                chain.proceed(request)
            }
            .build()
    }

    @Provides
    @Singleton
    fun providePreferencesManager(@ApplicationContext context: Context): PreferencesManager {
        return PreferencesManager(context)
    }

    @Provides
    @Singleton
    fun provideAuthService(
        okHttpClient: OkHttpClient,
        tokenExpiryInterceptor: TokenExpiryInterceptor,
    ): AuthService {
        val client = okHttpClient.newBuilder()
            .addInterceptor(tokenExpiryInterceptor)
            .build()
        return Retrofit.Builder()
            .baseUrl(RetrofitClient.BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(AuthService::class.java)
    }

    @Provides
    @Singleton
    fun provideApiService(
        @Named("apiClient") apiClient: OkHttpClient,
    ): ApiService {
        return Retrofit.Builder()
            .baseUrl(RetrofitClient.BASE_URL)
            .client(apiClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}

@EntryPoint
@InstallIn(SingletonComponent::class)
interface AuthServiceEntryPoint {
    fun authService(): AuthService
}

@EntryPoint
@InstallIn(SingletonComponent::class)
interface ApiServiceEntryPoint {
    fun apiService(): ApiService
}