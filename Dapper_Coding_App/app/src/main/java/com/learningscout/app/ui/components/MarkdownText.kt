package com.learningscout.app.ui.components

import android.util.Log
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.learningscout.app.ui.theme.GradientEnd
import com.learningscout.app.ui.theme.GradientStart

@Composable
fun MarkdownText(
    content: String,
    modifier: Modifier = Modifier,
) {
    if (content.isBlank()) {
        Text(
            text = content,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = modifier,
        )
        return
    }

    Column(modifier = modifier.fillMaxWidth()) {
        // Guard against overly long content that could cause ReDoS or OOM
        val safe = if (content.length > 10000) content.take(10000) + "…" else content
        val blocks = try {
            parseMarkdownBlocks(safe)
        } catch (e: Exception) {
            Log.e("MarkdownText", "parseMarkdownBlocks crash len=${safe.length}", e)
            emptyList()
        }
        for (block in blocks) {
            Spacer(modifier = Modifier.height(4.dp))
            when (block) {
                is MdBlock.Heading -> HeadingBlock(block)
                is MdBlock.CodeBlock -> CodeBlockView(block)
                is MdBlock.Blockquote -> BlockquoteView(block)
                is MdBlock.UnorderedList -> UnorderedListView(block)
                is MdBlock.OrderedList -> OrderedListView(block)
                is MdBlock.Paragraph -> ParagraphBlock(block)
            }
        }
    }
}

// ---- Block types ----

private sealed class MdBlock {
    data class Heading(val level: Int, val text: String) : MdBlock()
    data class CodeBlock(val language: String?, val code: String) : MdBlock()
    data class Blockquote(val lines: List<String>) : MdBlock()
    data class UnorderedList(val items: List<String>) : MdBlock()
    data class OrderedList(val items: List<String>) : MdBlock()
    data class Paragraph(val text: String) : MdBlock()
}

// ---- Parser ----

private fun parseMarkdownBlocks(content: String): List<MdBlock> {
    val blocks = mutableListOf<MdBlock>()

    // First, extract fenced code blocks
    val codeBlockRegex = Regex("```(\\w*)\n([\\s\\S]*?)```")
    val placeholders = mutableMapOf<String, MdBlock.CodeBlock>()
    var placeholderIdx = 0
    var processed = content.replace("\r\n", "\n")

    processed = codeBlockRegex.replace(processed) { match ->
        val lang = match.groupValues[1].trim().ifBlank { null }
        val code = match.groupValues[2].trimEnd()
        val key = "%%CODEBLOCK_${placeholderIdx++}%%"
        placeholders[key] = MdBlock.CodeBlock(lang, code)
        "\n$key\n"
    }

    // Split into lines and parse
    val lines = processed.lines()
    var i = 0
    while (i < lines.size) {
        val line = lines[i]
        when {
            // Code block placeholder
            line.contains("%%CODEBLOCK_") -> {
                val key = line.trim()
                placeholders[key]?.let { blocks.add(it) }
                i++
            }
            // Empty line
            line.isBlank() -> {
                i++
            }
            // Heading
            line.trimStart().startsWith("#") -> {
                val trimmed = line.trimStart()
                val level = trimmed.takeWhile { it == '#' }.length
                val text = trimmed.drop(level).trim()
                if (text.isNotBlank()) {
                    blocks.add(MdBlock.Heading(level.coerceIn(1, 6), text))
                }
                i++
            }
            // Blockquote
            line.trimStart().startsWith(">") -> {
                val quoteLines = mutableListOf<String>()
                while (i < lines.size && lines[i].trimStart().startsWith(">")) {
                    val q = lines[i].trimStart().removePrefix(">").trim()
                    if (q.isNotBlank()) quoteLines.add(q)
                    i++
                }
                if (quoteLines.isNotEmpty()) blocks.add(MdBlock.Blockquote(quoteLines))
            }
            // Unordered list
            line.trimStart().matches(Regex("^[-*+]\\s")) -> {
                val items = mutableListOf<String>()
                while (i < lines.size &&
                    (lines[i].trimStart().matches(Regex("^[-*+]\\s")) || lines[i].isBlank())
                ) {
                    if (lines[i].isBlank()) { i++; continue }
                    val item = lines[i].trimStart().replaceFirst(Regex("^[-*+]\\s"), "")
                    if (item.isNotBlank()) items.add(item)
                    i++
                }
                if (items.isNotEmpty()) blocks.add(MdBlock.UnorderedList(items))
            }
            // Ordered list
            line.trimStart().matches(Regex("^\\d+\\.\\s")) -> {
                val items = mutableListOf<String>()
                while (i < lines.size &&
                    (lines[i].trimStart().matches(Regex("^\\d+\\.\\s")) || lines[i].isBlank())
                ) {
                    if (lines[i].isBlank()) { i++; continue }
                    val item = lines[i].trimStart().replaceFirst(Regex("^\\d+\\.\\s"), "")
                    if (item.isNotBlank()) items.add(item)
                    i++
                }
                if (items.isNotEmpty()) blocks.add(MdBlock.OrderedList(items))
            }
            // Paragraph
            else -> {
                val paraLines = mutableListOf<String>()
                while (i < lines.size && lines[i].isNotBlank() &&
                    !lines[i].trimStart().startsWith("#") &&
                    !lines[i].trimStart().startsWith(">") &&
                    !lines[i].trimStart().matches(Regex("^[-*+]\\s")) &&
                    !lines[i].trimStart().matches(Regex("^\\d+\\.\\s")) &&
                    !lines[i].contains("%%CODEBLOCK_")
                ) {
                    paraLines.add(lines[i].trim())
                    i++
                }
                val para = paraLines.joinToString(" ").trim()
                if (para.isNotBlank()) blocks.add(MdBlock.Paragraph(para))
            }
        }
    }

    return blocks
}

// ---- Inline formatting ----

private data class InlineSpan(
    val text: String,
    val bold: Boolean = false,
    val italic: Boolean = false,
    val isCode: Boolean = false,
    val isLink: Boolean = false,
    val linkUrl: String = "",
)

private fun parseInlineSpans(text: String): List<InlineSpan> {
    // Guard against ReDoS on pathological input
    if (text.length > 5000) {
        return listOf(InlineSpan(text))
    }
    val spans = mutableListOf<InlineSpan>()
    // Pattern: code, bold+italic, bold, italic, link
    val regex = Regex(
        """(`[^`]+`)|(\*\*\*(.+?)\*\*\*)|(\*\*(.+?)\*\*)|(\*(.+?)\*)|(\[(.+?)\]\((.+?)\))"""
    )
    var matchCount = 0
    var lastIdx = 0

    for (match in regex.findAll(text)) {
        matchCount++
        if (matchCount > 500) break // prevent excessive processing
        // Text before match
        if (match.range.first > lastIdx) {
            val before = text.substring(lastIdx, match.range.first)
            if (before.isNotBlank()) spans.add(InlineSpan(before))
        }
        when {
            match.groupValues[1].isNotEmpty() -> { // `code`
                val code = match.groupValues[1].removeSurrounding("`")
                spans.add(InlineSpan(code, isCode = true))
            }
            match.groupValues[3].isNotEmpty() -> { // ***bold italic***
                spans.add(InlineSpan(match.groupValues[3], bold = true, italic = true))
            }
            match.groupValues[5].isNotEmpty() -> { // **bold**
                spans.add(InlineSpan(match.groupValues[5], bold = true))
            }
            match.groupValues[7].isNotEmpty() -> { // *italic*
                spans.add(InlineSpan(match.groupValues[7], italic = true))
            }
            match.groupValues[9].isNotEmpty() -> { // [text](url)
                spans.add(InlineSpan(match.groupValues[9], isLink = true, linkUrl = match.groupValues[10]))
            }
        }
        lastIdx = match.range.last + 1
    }
    // Remaining text
    if (lastIdx < text.length) {
        val remaining = text.substring(lastIdx)
        if (remaining.isNotBlank()) spans.add(InlineSpan(remaining))
    }
    if (spans.isEmpty()) {
        spans.add(InlineSpan(text))
    }
    return spans
}

@Composable
private fun InlineText(text: String, modifier: Modifier = Modifier) {
    val uriHandler = LocalUriHandler.current
    val spans = parseInlineSpans(text)
    val annotated = buildAnnotatedString {
        // Spans with isCode for background placement — track positions for post-processing
        for (span in spans) {
            val style = when {
                span.isCode -> SpanStyle(
                    fontFamily = FontFamily.Monospace,
                    fontSize = 13.sp,
                    background = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
                    color = MaterialTheme.colorScheme.primary,
                )
                span.isLink -> SpanStyle(
                    color = Color(0xFF1E90FF),
                    textDecoration = TextDecoration.Underline,
                    fontWeight = FontWeight.Medium,
                )
                span.bold && span.italic -> SpanStyle(
                    fontWeight = FontWeight.Bold,
                    fontStyle = FontStyle.Italic,
                )
                span.bold -> SpanStyle(fontWeight = FontWeight.Bold)
                span.italic -> SpanStyle(fontStyle = FontStyle.Italic)
                else -> SpanStyle()
            }
            withStyle(style) {
                append(span.text)
            }
        }
    }

    // For links, we use clickable annotations
    val linkSpans = spans.filter { it.isLink }
    if (linkSpans.isNotEmpty()) {
        val annotatedWithLinks = buildAnnotatedString {
            for (span in spans) {
                val start = length
                val style = when {
                    span.isCode -> SpanStyle(
                        fontFamily = FontFamily.Monospace,
                        fontSize = 13.sp,
                        background = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
                        color = MaterialTheme.colorScheme.primary,
                    )
                    span.isLink -> SpanStyle(
                        color = Color(0xFF1E90FF),
                        textDecoration = TextDecoration.Underline,
                        fontWeight = FontWeight.Medium,
                    )
                    span.bold && span.italic -> SpanStyle(
                        fontWeight = FontWeight.Bold,
                        fontStyle = FontStyle.Italic,
                    )
                    span.bold -> SpanStyle(fontWeight = FontWeight.Bold)
                    span.italic -> SpanStyle(fontStyle = FontStyle.Italic)
                    else -> SpanStyle()
                }
                withStyle(style) {
                    append(span.text)
                }
                if (span.isLink) {
                    val url = span.linkUrl
                    addStringAnnotation("URL", url, start, length)
                }
            }
        }

        androidx.compose.foundation.text.ClickableText(
            text = annotatedWithLinks,
            modifier = modifier,
            style = MaterialTheme.typography.bodyLarge.copy(
                color = MaterialTheme.colorScheme.onSurface,
            ),
            onClick = { offset ->
                annotatedWithLinks.getStringAnnotations("URL", offset, offset)
                    .firstOrNull()?.let { annotation ->
                        val url = if (annotation.item.startsWith("http"))
                            annotation.item else "https://${annotation.item}"
                        try { uriHandler.openUri(url) } catch (_: Exception) {}
                    }
            },
        )
    } else {
        Text(
            text = annotated,
            style = MaterialTheme.typography.bodyLarge,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = modifier,
        )
    }
}

// ---- Block composables ----

@Composable
private fun HeadingBlock(block: MdBlock.Heading) {
    val (style, topPadding) = when (block.level) {
        1 -> MaterialTheme.typography.headlineSmall to 8.dp
        2 -> MaterialTheme.typography.titleLarge to 6.dp
        else -> MaterialTheme.typography.titleMedium to 4.dp
    }
    Spacer(modifier = Modifier.height(topPadding))
    Text(
        text = block.text,
        style = style,
        fontWeight = FontWeight.Bold,
        color = MaterialTheme.colorScheme.onSurface,
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun CodeBlockView(block: MdBlock.CodeBlock) {
    Spacer(modifier = Modifier.height(2.dp))
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))
            .padding(12.dp),
    ) {
        Text(
            text = block.code.trimEnd(),
            style = MaterialTheme.typography.bodyMedium.copy(
                fontFamily = FontFamily.Monospace,
                fontSize = 13.sp,
                lineHeight = 20.sp,
            ),
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun BlockquoteView(block: MdBlock.Blockquote) {
    Spacer(modifier = Modifier.height(2.dp))
    Row(modifier = Modifier.fillMaxWidth()) {
        Box(
            modifier = Modifier
                .width(3.dp)
                .height((block.lines.size * 22).dp.coerceAtLeast(22.dp))
                .clip(RoundedCornerShape(2.dp))
                .background(
                    brush = androidx.compose.ui.graphics.Brush.verticalGradient(
                        listOf(GradientStart, GradientEnd)
                    )
                ),
        )
        Spacer(modifier = Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            for (line in block.lines) {
                Text(
                    text = line,
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 2.dp),
                )
            }
        }
    }
}

@Composable
private fun UnorderedListView(block: MdBlock.UnorderedList) {
    for (item in block.items) {
        Row(modifier = Modifier.fillMaxWidth().padding(start = 8.dp)) {
            Text(
                text = "  •",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.primary,
            )
            Spacer(modifier = Modifier.width(8.dp))
            Box(modifier = Modifier.weight(1f)) {
                InlineText(item)
            }
        }
        Spacer(modifier = Modifier.height(2.dp))
    }
}

@Composable
private fun OrderedListView(block: MdBlock.OrderedList) {
    for ((idx, item) in block.items.withIndex()) {
        Row(modifier = Modifier.fillMaxWidth().padding(start = 8.dp)) {
            Text(
                text = "${idx + 1}.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Medium,
            )
            Spacer(modifier = Modifier.width(8.dp))
            Box(modifier = Modifier.weight(1f)) {
                InlineText(item)
            }
        }
        Spacer(modifier = Modifier.height(2.dp))
    }
}

@Composable
private fun ParagraphBlock(block: MdBlock.Paragraph) {
    Spacer(modifier = Modifier.height(2.dp))
    InlineText(block.text)
}
