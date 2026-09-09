package com.ffassistant.sdk.ui

import android.Manifest
import android.app.AlertDialog
import android.content.Intent
import android.content.ClipData
import android.content.ClipboardManager
import android.content.pm.PackageManager
import android.content.Context
import android.view.Gravity
import android.os.Bundle
import android.speech.RecognizerIntent
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.ffassistant.sdk.FfAssistant
import com.ffassistant.sdk.R
import com.ffassistant.sdk.data.ChatRepository
import com.ffassistant.sdk.databinding.ActivityChatBinding
import com.ffassistant.sdk.network.AssistantResult
import com.ffassistant.sdk.network.ChatMessage
import com.ffassistant.sdk.network.Feedback
import com.ffassistant.sdk.network.Sender
import com.google.android.material.button.MaterialButton
import com.google.android.material.card.MaterialCardView
import kotlinx.coroutines.launch
import java.util.UUID

private const val VOICE_REQUEST_CODE = 701
private const val MAX_SUGGESTIONS = 5
private const val WELCOME_MESSAGE = "Hi there! I’m here to help with your Flying Flea support."
private const val SERVICE_REMINDER_QUESTION = "Why is the service reminder still showing?"
private const val CLOUD_CONNECTION_QUESTION = "Why is my vehicle not connecting to the cloud?"
private val DEFAULT_SUGGESTIONS = listOf(
    "Why is my map not working?",
    "Why am I not getting the OTP?",
    "Why does the app log me out automatically?",
    "Why is my vehicle data not syncing?",
    "Why does my Wi-Fi disconnect when I open the app?"
)

private const val PREFS = "ff_assistant_cache"
private const val KEY_DARK_MODE = "dark_mode_enabled"

class ChatActivity : AppCompatActivity() {
    private lateinit var binding: ActivityChatBinding
    private lateinit var repository: ChatRepository
    private val messages = mutableListOf<ChatMessage>()
    private lateinit var adapter: MessageAdapter
    private val quickSuggestions = mutableListOf<String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        applyPersistedTheme()
        super.onCreate(savedInstanceState)
        binding = ActivityChatBinding.inflate(layoutInflater)
        setContentView(binding.root)

        repository = ChatRepository(FfAssistant.context())
        adapter = MessageAdapter(messages, ::onFeedback, ::raiseTicket, ::submitQuestion)
        binding.messages.layoutManager = LinearLayoutManager(this)
        binding.messages.adapter = adapter

        val cachedMessages = repository.loadMessages()
        if (cachedMessages.isNotEmpty()) {
            messages.addAll(cachedMessages)
            adapter.notifyDataSetChanged()
        } else {
            val welcome = repository.assistantMessage(WELCOME_MESSAGE, -1)
            messages.add(welcome)
            repository.saveMessage(welcome)
            adapter.notifyItemInserted(messages.lastIndex)
        }

        quickSuggestions.clear()
        val cachedSuggestions = repository.loadSuggestions()
        quickSuggestions.addAll(
            (cachedSuggestions.ifEmpty { DEFAULT_SUGGESTIONS })
                .filterNot { it == SERVICE_REMINDER_QUESTION || it == CLOUD_CONNECTION_QUESTION }
                .take(MAX_SUGGESTIONS)
        )
        adapter.setSuggestions(quickSuggestions)

        binding.send.setOnClickListener { sendMessage() }
        binding.backButton.setOnClickListener { finish() }
        binding.menuButton.setOnClickListener { showOverflowMenu(it) }
        binding.micButton.setOnClickListener { startVoiceInput() }
    }

    private fun startVoiceInput() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), VOICE_REQUEST_CODE)
            return
        }

        val voiceIntent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_PROMPT, getString(R.string.voice_input))
        }
        if (voiceIntent.resolveActivity(packageManager) == null) {
            Toast.makeText(this, R.string.voice_not_available, Toast.LENGTH_SHORT).show()
            return
        }
        startActivityForResult(voiceIntent, VOICE_REQUEST_CODE)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == VOICE_REQUEST_CODE && grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
            startVoiceInput()
        }
    }

    @Suppress("DEPRECATION")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == VOICE_REQUEST_CODE && resultCode == RESULT_OK) {
            data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                ?.firstOrNull()
                ?.let { binding.input.setText(it) }
        }
    }

    private fun applyPersistedTheme() {
        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val darkMode = prefs.getBoolean(KEY_DARK_MODE, resources.configuration.uiMode and
            android.content.res.Configuration.UI_MODE_NIGHT_MASK == android.content.res.Configuration.UI_MODE_NIGHT_YES)
        AppCompatDelegate.setDefaultNightMode(
            if (darkMode) AppCompatDelegate.MODE_NIGHT_YES else AppCompatDelegate.MODE_NIGHT_NO
        )
    }

    private fun showOverflowMenu(anchor: View) {
        val prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val isDark = AppCompatDelegate.getDefaultNightMode() == AppCompatDelegate.MODE_NIGHT_YES
        PopupMenu(this, anchor).apply {
            menu.add(0, R.id.menu_raise_ticket, 0, getString(R.string.raise_ticket)).setIcon(R.drawable.ic_ticket)
            menu.add(0, R.id.menu_clear_chat, 1, getString(R.string.clear_chat)).setIcon(R.drawable.ic_delete)
            menu.add(0, R.id.menu_theme, 2, if (isDark) getString(R.string.light_mode) else getString(R.string.dark_mode)).setIcon(R.drawable.ic_theme)
            setOnMenuItemClickListener {
                when (it.itemId) {
                    R.id.menu_raise_ticket -> raiseTicket(null)
                    R.id.menu_clear_chat -> confirmClearConversation()
                    R.id.menu_theme -> {
                        val next = !isDark
                        prefs.edit().putBoolean(KEY_DARK_MODE, next).apply()
                        AppCompatDelegate.setDefaultNightMode(
                            if (next) AppCompatDelegate.MODE_NIGHT_YES else AppCompatDelegate.MODE_NIGHT_NO
                        )
                        recreate()
                    }
                }
                true
            }
            try {
                val method = PopupMenu::class.java.getDeclaredMethod("setForceShowIcon", Boolean::class.javaPrimitiveType)
                method.isAccessible = true
                method.invoke(this, true)
            } catch (_: ReflectiveOperationException) {
                // Older Android PopupMenu implementations may not expose icon support.
            }
            show()
        }
    }

    private fun confirmClearConversation() {
        AlertDialog.Builder(this)
            .setTitle(R.string.clear_chat_title)
            .setMessage(R.string.clear_chat_body)
            .setNegativeButton(R.string.cancel, null)
            .setPositiveButton(android.R.string.ok) { _, _ ->
                repository.clearMessages()
                messages.clear()
                val welcome = repository.assistantMessage(WELCOME_MESSAGE, -1)
                messages.add(welcome)
                repository.saveMessage(welcome)
                adapter.notifyDataSetChanged()
            }
            .show()
    }

    private fun submitQuestion(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty() || binding.loading.visibility == View.VISIBLE) return

        val userMessage = repository.userMessage(trimmed)
        messages += userMessage
        repository.saveMessage(userMessage)
        adapter.notifyItemInserted(messages.lastIndex)
        binding.messages.scrollToPosition(messages.lastIndex)
        binding.input.setText("")
        binding.loading.visibility = View.VISIBLE
        binding.send.isEnabled = false

        lifecycleScope.launch {
            try {
                val result = repository.send(trimmed)
                val responseText: String
                val retrievedCount: Int
                val suggestions: List<String>

                when (result) {
                    is AssistantResult.Success -> {
                        val body = result.value
                        responseText = body.answer
                        retrievedCount = body.retrieved_count
                        suggestions = body.suggestions
                    }
                    is AssistantResult.Failure -> {
                        responseText = result.error.userMessage
                        retrievedCount = 0
                        suggestions = emptyList()
                    }
                }

                if (suggestions.isNotEmpty()) {
                    quickSuggestions.clear()
                    quickSuggestions.addAll(
                        suggestions
                            .filterNot { it == SERVICE_REMINDER_QUESTION || it == CLOUD_CONNECTION_QUESTION }
                            .take(MAX_SUGGESTIONS)
                    )
                    repository.saveSuggestions(quickSuggestions)
                    adapter.setSuggestions(quickSuggestions)
                }

                val assistantMessage = repository.assistantMessage(responseText, retrievedCount)
                messages += assistantMessage
                repository.saveMessage(assistantMessage)
                adapter.notifyItemInserted(messages.lastIndex)
                binding.messages.scrollToPosition(messages.lastIndex)
            } catch (_: Exception) {
                val errorMessage = repository.assistantMessage(getString(R.string.chat_retry_message), 0)
                messages += errorMessage
                repository.saveMessage(errorMessage)
                adapter.notifyItemInserted(messages.lastIndex)
                binding.messages.scrollToPosition(messages.lastIndex)
            } finally {
                binding.loading.visibility = View.GONE
                binding.send.isEnabled = true
            }
        }
    }

    private fun sendMessage() {
        submitQuestion(binding.input.text.toString())
    }

    private fun onFeedback(message: ChatMessage, feedback: Feedback) {
        val index = messages.indexOfFirst { it.id == message.id }
        if (index == -1) return
        val updated = message.copy(feedback = feedback)
        messages[index] = updated
        repository.updateMessage(updated)
        adapter.notifyItemChanged(index)
        if (feedback == Feedback.UP) {
            showRatingDialog()
        }
        // TODO: wire to your analytics/feedback endpoint once one exists;
        // the backend contract in this project doesn't define one yet.
    }

    private fun raiseTicket(message: ChatMessage?) {
        if (message == null) {
            showManualTicketDialog()
            return
        }
        val assistantIndex = message?.let { selected ->
            messages.indexOfFirst { item -> item.id == selected.id }
        } ?: -1
        val userQuestion = if (assistantIndex > 0) {
            messages.subList(0, assistantIndex)
                .lastOrNull { it.sender == Sender.USER }
                ?.text
        } else {
            messages.lastOrNull { it.sender == Sender.USER }?.text
        }
        val answer = message?.text
            ?: messages.lastOrNull { it.sender == Sender.ASSISTANT }?.text
            ?: getString(R.string.ticket_default_summary)
        val summary = listOfNotNull(
            userQuestion?.let { "Question: $it" },
            "Assistant response: $answer"
        ).joinToString("\n\n")
        val content = layoutInflater.inflate(R.layout.dialog_ticket_review, null)
        val description = content.findViewById<android.widget.EditText>(R.id.ticketDescription)
        description.setText(summary)
        description.setSelection(description.text.length)
        val dialog = AlertDialog.Builder(this)
            .setView(content)
            .create()
        content.findViewById<View>(R.id.cancelTicket).setOnClickListener { dialog.dismiss() }
        val submitButton = content.findViewById<MaterialButton>(R.id.submitTicket)
        submitButton.setOnClickListener {
            submitTicket(
                dialog = dialog,
                submitButton = submitButton,
                title = userQuestion ?: getString(R.string.ticket_default_title),
                description = description.text.toString().trim(),
                source = "chat"
            )
        }
        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        dialog.window?.setLayout(
            (resources.displayMetrics.widthPixels * 0.92).toInt(),
            android.view.WindowManager.LayoutParams.WRAP_CONTENT
        )
    }

    private fun showManualTicketDialog() {
        val content = layoutInflater.inflate(R.layout.dialog_ticket_manual, null)
        val title = content.findViewById<android.widget.EditText>(R.id.ticketTitle)
        val description = content.findViewById<android.widget.EditText>(R.id.ticketDescription)
        val dialog = AlertDialog.Builder(this)
            .setView(content)
            .create()

        content.findViewById<View>(R.id.cancelTicket).setOnClickListener { dialog.dismiss() }
        val submitButton = content.findViewById<MaterialButton>(R.id.submitTicket)
        submitButton.setOnClickListener {
            val issueTitle = title.text.toString().trim()
            val issueDescription = description.text.toString().trim()
            if (issueTitle.isEmpty()) {
                title.error = getString(R.string.ticket_title_required)
                title.requestFocus()
                return@setOnClickListener
            }
            if (issueDescription.isEmpty()) {
                description.error = getString(R.string.ticket_description_required)
                description.requestFocus()
                return@setOnClickListener
            }
            submitTicket(dialog, submitButton, issueTitle, issueDescription, "menu")
        }

        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        dialog.window?.setLayout(
            (resources.displayMetrics.widthPixels * 0.92).toInt(),
            android.view.WindowManager.LayoutParams.WRAP_CONTENT
        )
    }

    private fun submitTicket(
        dialog: AlertDialog,
        submitButton: MaterialButton,
        title: String,
        description: String,
        source: String
    ) {
        if (submitButton.isEnabled.not()) return
        submitButton.isEnabled = false
        submitButton.text = getString(R.string.ticket_submitting)
        lifecycleScope.launch {
            when (val result = repository.createTicket(title, description, source)) {
                is AssistantResult.Success -> {
                    dialog.dismiss()
                    showTicketSuccess(result.value.reference_id)
                }
                is AssistantResult.Failure -> {
                    submitButton.isEnabled = true
                    submitButton.text = getString(R.string.raise_ticket)
                    Toast.makeText(this@ChatActivity, result.error.userMessage, Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun showTicketSuccess(referenceId: String) {
        val content = layoutInflater.inflate(R.layout.dialog_ticket_success, null)
        content.findViewById<TextView>(R.id.ticketReference).text = referenceId
        val dialog = AlertDialog.Builder(this)
            .setView(content)
            .create()
        content.findViewById<View>(R.id.copyTicketReference).setOnClickListener {
            val clipboard = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
            clipboard.setPrimaryClip(ClipData.newPlainText("Ticket reference", referenceId))
            Toast.makeText(this, R.string.ticket_reference_copied, Toast.LENGTH_SHORT).show()
        }
        content.findViewById<View>(R.id.dismissTicket).setOnClickListener { dialog.dismiss() }
        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        dialog.window?.setLayout(
            (resources.displayMetrics.widthPixels * 0.92).toInt(),
            android.view.WindowManager.LayoutParams.WRAP_CONTENT
        )
    }

    private fun showRatingDialog() {
        val content = layoutInflater.inflate(R.layout.dialog_rating, null)
        val dialog = AlertDialog.Builder(this)
            .setView(content)
            .create()
        content.findViewById<View>(R.id.dismissRating).setOnClickListener { dialog.dismiss() }
        content.findViewById<View>(R.id.submitRating).setOnClickListener {
            val selected = content.findViewById<android.widget.RadioGroup>(R.id.ratingGroup)
                .checkedRadioButtonId
            if (selected == -1) {
                Toast.makeText(this, R.string.rating_required, Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            dialog.dismiss()
            Toast.makeText(this, R.string.rating_thanks, Toast.LENGTH_SHORT).show()
        }
        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        dialog.window?.setLayout(
            (resources.displayMetrics.widthPixels * 0.92).toInt(),
            android.view.WindowManager.LayoutParams.WRAP_CONTENT
        )
    }
}

private const val VIEW_TYPE_USER = 0
private const val VIEW_TYPE_ASSISTANT = 1

private class MessageAdapter(
    private val items: List<ChatMessage>,
    private val onFeedback: (ChatMessage, Feedback) -> Unit,
    private val onRaiseTicket: (ChatMessage) -> Unit,
    private val onSuggestionClick: (String) -> Unit
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private var suggestions: List<String> = emptyList()

    fun setSuggestions(value: List<String>) {
        suggestions = value.take(MAX_SUGGESTIONS)
        notifyItemChanged(0)
    }

    class UserHolder(view: View) : RecyclerView.ViewHolder(view)
    class AssistantHolder(view: View) : RecyclerView.ViewHolder(view)

    override fun getItemViewType(position: Int): Int =
        if (items[position].sender == Sender.USER) VIEW_TYPE_USER else VIEW_TYPE_ASSISTANT

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return if (viewType == VIEW_TYPE_USER) {
            UserHolder(inflater.inflate(R.layout.item_message_user, parent, false))
        } else {
            AssistantHolder(inflater.inflate(R.layout.item_message_assistant, parent, false))
        }
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = items[position]
        when (holder) {
            is UserHolder -> bindUser(holder, message)
            is AssistantHolder -> bindAssistant(holder, message)
        }
    }

    private fun bindUser(holder: UserHolder, message: ChatMessage) {
        val card = holder.itemView as MaterialCardView
        card.findViewById<TextView>(R.id.messageText).text = message.text
    }

    private fun bindAssistant(holder: AssistantHolder, message: ChatMessage) {
        val card = holder.itemView as MaterialCardView
        val textView = card.findViewById<TextView>(R.id.messageText)
        textView.text = message.text

        val suggestionContainer = card.findViewById<LinearLayout>(R.id.quickSuggestionsContainer)
        suggestionContainer.removeAllViews()
        val showSuggestions = message.retrievedCount == -1 && suggestions.isNotEmpty()
        suggestionContainer.visibility = if (showSuggestions) View.VISIBLE else View.GONE
        if (showSuggestions) {
            suggestions.forEach { suggestion ->
                val chip = MaterialButton(holder.itemView.context).apply {
                    text = suggestion
                    isAllCaps = false
                    gravity = Gravity.CENTER_VERTICAL or Gravity.START
                    setTextAppearance(com.google.android.material.R.style.TextAppearance_Material3_BodyMedium)
                    minHeight = 0
                    minWidth = 0
                    setPadding(20, 12, 20, 12)
                    setBackgroundColor(context.getColor(R.color.ff_surface))
                    setTextColor(context.getColor(R.color.ff_ink))
                    strokeWidth = 1
                    strokeColor = context.getColorStateList(R.color.ff_line)
                    cornerRadius = 18
                    setOnClickListener { onSuggestionClick(suggestion) }
                    layoutParams = LinearLayout.LayoutParams(
                        ViewGroup.LayoutParams.MATCH_PARENT,
                        ViewGroup.LayoutParams.WRAP_CONTENT
                    ).apply { bottomMargin = 8 }
                }
                suggestionContainer.addView(chip)
            }
        }

        val noAnswerBanner = card.findViewById<LinearLayout>(R.id.noAnswerBanner)
            val needsTicket = message.retrievedCount >= 0 && message.feedback == Feedback.DOWN
            noAnswerBanner.visibility = if (needsTicket) View.VISIBLE else View.GONE
            if (needsTicket) {
            card.findViewById<MaterialButton>(R.id.inlineRaiseTicket).setOnClickListener {
                onRaiseTicket(message)
            }
        }

        val thumbUp = card.findViewById<MaterialButton>(R.id.thumbUp)
        val thumbDown = card.findViewById<MaterialButton>(R.id.thumbDown)
        val feedbackPrompt = card.findViewById<TextView>(R.id.feedbackPrompt)

        when (message.feedback ?: Feedback.NONE) {
            Feedback.NONE -> {
                feedbackPrompt.setText(R.string.was_this_helpful)
                thumbUp.isEnabled = true
                thumbDown.isEnabled = true
            }
            else -> {
                    feedbackPrompt.setText(
                        if (message.feedback == Feedback.UP) R.string.feedback_thanks
                        else R.string.was_this_helpful
                    )
                thumbUp.isEnabled = false
                thumbDown.isEnabled = false
            }
        }

        thumbUp.setOnClickListener { onFeedback(message, Feedback.UP) }
        thumbDown.setOnClickListener { onFeedback(message, Feedback.DOWN) }
    }
}
