package com.learningscout.app.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.learningscout.app.data.local.dao.ChatDao
import com.learningscout.app.data.local.entity.ChatMessageEntity
import com.learningscout.app.data.local.entity.ChatSessionEntity

@Database(entities = [ChatMessageEntity::class, ChatSessionEntity::class], version = 3, exportSchema = false)
abstract class AppDatabase : RoomDatabase() {
    abstract fun chatDao(): ChatDao

    companion object {
        val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE chat_messages ADD COLUMN thinking TEXT NOT NULL DEFAULT ''")
            }
        }
    }
}
