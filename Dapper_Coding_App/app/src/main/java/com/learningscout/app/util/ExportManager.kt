package com.learningscout.app.util

import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import android.net.Uri
import androidx.core.content.FileProvider
import com.learningscout.app.data.local.entity.ChatMessageEntity
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object ExportManager {

    private val dateFormat = SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault())
    private val fileDateFormat = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault())

    fun exportCsv(context: Context, messages: List<ChatMessageEntity>, title: String) {
        val sb = StringBuilder()
        sb.appendLine("序号,时间,角色,内容")
        messages.forEachIndexed { index, msg ->
            val time = dateFormat.format(Date(msg.timestamp))
            val role = if (msg.role == "user") "用户" else "AI"
            val content = msg.content.replace("\"", "\"\"").replace("\n", " ")
            sb.appendLine("${index + 1},$time,$role,\"$content\"")
        }

        val fileName = "学习记录_${fileDateFormat.format(Date())}.csv"
        val file = File(context.cacheDir, fileName)
        file.writeText(sb.toString(), Charsets.UTF_8)

        shareFile(context, file, "text/csv")
    }

    fun exportPdf(context: Context, messages: List<ChatMessageEntity>, title: String) {
        var document: PdfDocument? = null
        try {
            document = PdfDocument()
            val pageInfo = PdfDocument.PageInfo.Builder(595, 842, 1).create() // A4
            val page = document.startPage(pageInfo)
            val canvas: Canvas = page.canvas

            val titlePaint = Paint().apply {
                color = android.graphics.Color.parseColor("#1A1A2E")
                textSize = 22f
                typeface = Typeface.DEFAULT_BOLD
                isAntiAlias = true
            }
            val headerPaint = Paint().apply {
                color = android.graphics.Color.parseColor("#4355DB")
                textSize = 14f
                typeface = Typeface.DEFAULT_BOLD
                isAntiAlias = true
            }
            val bodyPaint = Paint().apply {
                color = android.graphics.Color.parseColor("#333333")
                textSize = 12f
                isAntiAlias = true
            }
            val datePaint = Paint().apply {
                color = android.graphics.Color.parseColor("#999999")
                textSize = 10f
                isAntiAlias = true
            }
            val linePaint = Paint().apply {
                color = android.graphics.Color.parseColor("#E0E0E0")
                strokeWidth = 1f
            }

            var y = 60f
            val leftMargin = 50f
            val rightMargin = 545f
            val contentWidth = rightMargin - leftMargin

            canvas.drawText("学习摘要", leftMargin, y, titlePaint)
            y += 30f
            canvas.drawText(title, leftMargin, y, headerPaint)
            y += 12f
            canvas.drawText("导出时间: ${dateFormat.format(Date())}", leftMargin, y, datePaint)
            y += 30f
            canvas.drawLine(leftMargin, y, rightMargin, y, linePaint)
            y += 20f

            for (msg in messages) {
                if (y > 790f) break
                val roleLabel = if (msg.role == "user") "用户" else "AI 导师"
                canvas.drawText(roleLabel, leftMargin, y, headerPaint)
                y += 16f
                val content = msg.content.take(500)
                val lines = wrapText(content, bodyPaint, contentWidth)
                for (line in lines) {
                    if (y > 800f) break
                    canvas.drawText(line, leftMargin, y, bodyPaint)
                    y += 16f
                }
                y += 8f
            }

            y = 810f
            canvas.drawLine(leftMargin, y, rightMargin, y, linePaint)
            y += 16f
            canvas.drawText("© 2026 Learning Scout — 你的认知状态追踪器", leftMargin, y, datePaint)

            document.finishPage(page)

            val fileName = "学习摘要_${fileDateFormat.format(Date())}.pdf"
            val file = File(context.cacheDir, fileName)
            file.outputStream().use { document.writeTo(it) }
            shareFile(context, file, "application/pdf")
        } catch (e: Exception) {
            android.util.Log.e("ExportManager", "PDF export failed", e)
        } finally {
            document?.close()
        }
    }

    private fun wrapText(text: String, paint: Paint, maxWidth: Float): List<String> {
        val lines = mutableListOf<String>()
        var current = StringBuilder()
        for (char in text) {
            val test = current.toString() + char
            if (paint.measureText(test) > maxWidth && current.isNotEmpty()) {
                lines.add(current.toString())
                current = StringBuilder().append(char)
            } else {
                current.append(char)
            }
        }
        if (current.isNotEmpty()) lines.add(current.toString())
        return lines.ifEmpty { listOf(text) }
    }

    private fun shareFile(context: Context, file: File, mimeType: String) {
        val uri: Uri = FileProvider.getUriForFile(
            context,
            "${context.packageName}.fileprovider",
            file,
        )
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = mimeType
            putExtra(Intent.EXTRA_STREAM, uri)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        context.startActivity(Intent.createChooser(intent, "分享文件"))
    }
}
