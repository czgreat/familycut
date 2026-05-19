package com.cz.familycut

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.room.Room
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.cz.familycut.data.local.AppDatabase
import com.cz.familycut.data.local.ThemePreferencesRepository
import com.cz.familycut.data.remote.NetworkModule
import com.cz.familycut.data.repository.AppStateRepository
import com.cz.familycut.data.repository.FoodPresetRepository
import com.cz.familycut.data.repository.SyncRepository
import com.cz.familycut.ui.FamilyCutApp
import com.cz.familycut.ui.viewmodel.MainViewModel

private val Migration1To2 = object : Migration(1, 2) {
    override fun migrate(database: SupportSQLiteDatabase) {
        database.execSQL("ALTER TABLE food_presets ADD COLUMN actualGrams REAL NOT NULL DEFAULT 100")
        database.execSQL("ALTER TABLE food_presets ADD COLUMN sodiumMg REAL")
        database.execSQL("ALTER TABLE food_presets ADD COLUMN note TEXT")
    }
}

class MainActivity : ComponentActivity() {
    private val database by lazy {
        Room.databaseBuilder(
            applicationContext,
            AppDatabase::class.java,
            "familycut.db"
        )
            .addMigrations(Migration1To2)
            .build()
    }

    private val preferencesRepository by lazy {
        ThemePreferencesRepository(applicationContext)
    }

    private val appStateRepository by lazy {
        AppStateRepository(
            apiServiceFactory = NetworkModule::apiService,
            preferencesRepository = preferencesRepository
        )
    }

    private val foodPresetRepository by lazy {
        FoodPresetRepository(database.appDao())
    }

    private val viewModel by viewModels<MainViewModel> {
        MainViewModel.factory(
            themeRepository = preferencesRepository,
            appStateRepository = appStateRepository,
            syncRepository = SyncRepository(
                appDao = database.appDao(),
                apiServiceFactory = NetworkModule::apiService,
                preferencesRepository = preferencesRepository,
                sessionProvider = { appStateRepository.session.value }
            ),
            foodPresetRepository = foodPresetRepository
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            FamilyCutApp(viewModel = viewModel)
        }
    }
}
