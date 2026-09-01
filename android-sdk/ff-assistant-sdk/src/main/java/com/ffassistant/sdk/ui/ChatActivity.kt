package com.ffassistant.sdk.ui

import android.app.AlertDialog
import android.content.Context
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.PopupMenu
import android.widget.TextView
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

private const val PREFS = "ff_assistant_cache"
private const val KEY_DARK_MODE = "dark_mode_enabled"

class ChatActivity : AppCompatActivity() {
    private lateinit var binding: ActivityChatBinding
    private lateinit var repository: ChatRepository
    private val messages = mutableListOf<ChatMessage>()
    private lateinit var adapter: MessageAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        applyPersistedTheme()
        super.onCreate(savedInstanceState)
        binding = ActivityChatBinding.inflate(layoutInflater)
        setContentView(binding.root)

        repository = ChatRepository(FfAssistant.context())
        adapter = MessageAdapter(messages, ::onFeedback, ::raiseTicket)
        binding.messages.layoutManager = LinearLayoutManager(this)
        binding.messages.adapter = adapter

        val cachedMessages = repository.loadMessages()
        if (cachedMessages.isNotEmpty()) {
            messages.addAll(cachedMessages)
            adapter.notifyDataSetChanged()
        }

        binding.send.setOnClickListener { sendMessage() }
        binding.backButton.setOnClickListener { finish() }
        binding.menuButton.setOnClickListener { showOverflowMenu(it) }
        // TODO: wire attachButton/micButton to real file-picker and speech-to-text
        // flows when those capabilities are added to the backend contract.
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
            menu.add(0, R.id.menu_raise_ticket, 0, getString(R.string.raise_ticket))
            menu.add(0, R.id.menu_clear_chat, 1, getString(R.string.clear_chat))
            menu.add(0, R.id.menu_support_profile, 2, getString(R.string.support_profile))
            menu.add(0, R.id.menu_theme, 3, if (isDark) getString(R.string.light_mode) else getString(R.string.dark_mode))
            setOnMenuItemClickListener {
                when (it.itemId) {
                    R.id.menu_raise_ticket -> raiseTicket(null)
                    R.id.menu_clear_chat -> confirmClearConversation()
                    R.id.menu_support_profile -> showSupportProfile()
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
                adapter.notifyDataSetChanged()
            }
            .show()
    }

    private fun showSupportProfile() {
        AlertDialog.Builder(this)
            .setTitle(R.string.profile_title)
            .setMessage(R.string.profile_body)
            .setPositiveButton(android.R.string.ok, null)
            .show()
    }

    private fun sendMessage() {
        val text = binding.input.text.toString().trim()
        if (text.isEmpty() || binding.loading.visibility == View.VISIBLE) return

        val userMessage = repository.userMessage(text)
        messages += userMessage
        repository.saveMessage(userMessage)
        adapter.notifyItemInserted(messages.lastIndex)
        binding.messages.scrollToPosition(messages.lastIndex)
        binding.input.text?.clear()
        binding.loading.visibility = View.VISIBLE
        binding.send.isEnabled = false

        lifecycleScope.launch {
            val result = repository.send(text)
            // retrievedCount == 0 means the RAG pipeline found no matching
            // documents for this query; the UI (not the backend) decides to
            // surface a "raise a ticket" prompt in that case.
            val (responseText, retrievedCount) = when (result) {
                is AssistantResult.Success -> result.value.answer to result.value.retrieved_count
                is AssistantResult.Failure -> result.error.userMessage to 0
            }

            val assistantMessage = repository.assistantMessage(responseText, retrievedCount)
            messages += assistantMessage
            repository.saveMessage(assistantMessage)
            adapter.notifyItemInserted(messages.lastIndex)
            binding.messages.scrollToPosition(messages.lastIndex)
            binding.loading.visibility = View.GONE
            binding.send.isEnabled = true
        }
    }

    private fun onFeedback(message: ChatMessage, feedback: Feedback) {
        val index = messages.indexOfFirst { it.id == message.id }
        if (index == -1) return
        val updated = message.copy(feedback = feedback)
        messages[index] = updated
        repository.updateMessage(updated)
        adapter.notifyItemChanged(index)
        // TODO: wire to your analytics/feedback endpoint once one exists;
        // the backend contract in this project doesn't define one yet.
    }

    private fun raiseTicket(message: ChatMessage?) {
        val referenceId = UUID.randomUUID().toString().take(8).uppercase()
        // TODO: replace with a real POST to your ticketing backend/CRM.
        // This is intentionally UI-only per the current scope: the button
        // and confirmation flow are wired, the network call is not.
        AlertDialog.Builder(this)
            .setTitle(R.string.ticket_raised_title)
            .setMessage(getString(R.string.ticket_raised_body, referenceId))
            .setPositiveButton(android.R.string.ok, null)
            .show()
    }
}

private const val VIEW_TYPE_USER = 0
private const val VIEW_TYPE_ASSISTANT = 1

private class MessageAdapter(
    private val items: List<ChatMessage>,
    private val onFeedback: (ChatMessage, Feedback) -> Unit,
    private val onRaiseTicket: (ChatMessage) -> Unit
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

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

        val noAnswerBanner = card.findViewById<LinearLayout>(R.id.noAnswerBanner)
        val foundNoAnswer = message.retrievedCount == 0
        noAnswerBanner.visibility = if (foundNoAnswer) View.VISIBLE else View.GONE
        if (foundNoAnswer) {
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
                feedbackPrompt.setText(R.string.feedback_thanks)
                thumbUp.isEnabled = false
                thumbDown.isEnabled = false
            }
        }

        thumbUp.setOnClickListener { onFeedback(message, Feedback.UP) }
        thumbDown.setOnClickListener { onFeedback(message, Feedback.DOWN) }
    }
}
