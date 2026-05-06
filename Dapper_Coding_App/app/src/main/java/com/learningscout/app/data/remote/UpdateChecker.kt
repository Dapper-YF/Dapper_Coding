package com.learningscout.app.data.remote

import android.app.DownloadManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.net.Uri
import androidx.core.content.FileProvider
import com.learningscout.app.BuildConfig
import com.learningscout.app.data.remote.dto.AppVersionResponse
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import com.google.gson.Gson
import java.io.File

object UpdateChecker {
    private val gson = Gson()
    private val client = OkHttpClient()

    suspend fun checkForUpdate(): AppVersionResponse? = withContext(Dispatchers.IO) {
        try {
            val request = Request.Builder()
                .url("${RetrofitClient.BASE_URL}api/app/version")
                .get()
                .build()
            val response = client.newCall(request).execute()
            if (response.isSuccessful) {
                response.body?.string()?.let { gson.fromJson(it, AppVersionResponse::class.java) }
            } else null
        } catch (_: Exception) {
            null
        }
    }

    fun hasUpdate(serverVersion: AppVersionResponse): Boolean {
        return serverVersion.version > BuildConfig.VERSION_CODE
    }

    fun downloadAndInstall(context: Context, url: String) {
        val file = File(context.cacheDir, "app-update.apk")
        if (file.exists()) file.delete()

        val request = DownloadManager.Request(Uri.parse(url))
            .setTitle("Learning Scout 更新")
            .setDescription("正在下载新版本...")
            .setDestinationUri(Uri.fromFile(file))
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)

        val dm = context.getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        val downloadId = dm.enqueue(request)

        val onComplete = object : BroadcastReceiver() {
            override fun onReceive(ctx: Context, intent: Intent) {
                val id = intent.getLongExtra(DownloadManager.EXTRA_DOWNLOAD_ID, -1)
                if (id != downloadId) return
                ctx.unregisterReceiver(this)

                val apkFile = File(ctx.cacheDir, "app-update.apk")
                if (!apkFile.exists()) return

                val apkUri = FileProvider.getUriForFile(
                    ctx,
                    "${ctx.packageName}.fileprovider",
                    apkFile,
                )
                val installIntent = Intent(Intent.ACTION_VIEW).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    setDataAndType(apkUri, "application/vnd.android.package-archive")
                }
                ctx.startActivity(installIntent)
            }
        }

        context.registerReceiver(
            onComplete,
            IntentFilter(DownloadManager.ACTION_DOWNLOAD_COMPLETE),
            Context.RECEIVER_EXPORTED,
        )
    }
}
