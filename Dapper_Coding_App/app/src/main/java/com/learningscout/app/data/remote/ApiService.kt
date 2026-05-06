package com.learningscout.app.data.remote

import com.learningscout.app.data.remote.dto.ChatRequest
import com.learningscout.app.data.remote.dto.ConversationDto
import com.learningscout.app.data.remote.dto.DailyLessonResponse
import com.learningscout.app.data.remote.dto.DigestResponse
import com.learningscout.app.data.remote.dto.UserStatsDto
import com.learningscout.app.data.remote.dto.SummarizeRequest
import com.learningscout.app.data.remote.dto.SummarizeResponse
import com.learningscout.app.data.remote.dto.HistoryMessageDto
import okhttp3.ResponseBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ApiService {
    @POST("api/chat")
    suspend fun sendMessage(@Body request: ChatRequest): Response<ResponseBody>

    @GET("api/digest/latest")
    suspend fun getLatestDigest(): DigestResponse

    @GET("api/conversations")
    suspend fun getConversations(): List<ConversationDto>

    @GET("api/conversations/{id}/history")
    suspend fun getConversationHistory(@Path("id") conversationId: String): List<HistoryMessageDto>

    @DELETE("api/conversations/{id}")
    suspend fun deleteConversation(@Path("id") conversationId: String): Response<ResponseBody>

    @GET("api/user/stats")
    suspend fun getUserStats(): UserStatsDto

    @GET("api/lesson/recommend")
    suspend fun getDailyLesson(): DailyLessonResponse

    @POST("api/chat/summarize")
    suspend fun summarize(@Body request: SummarizeRequest): SummarizeResponse
}
