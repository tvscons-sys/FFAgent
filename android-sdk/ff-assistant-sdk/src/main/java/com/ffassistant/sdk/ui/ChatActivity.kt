package com.ffassistant.sdk.ui

import android.os.Bundle
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.ffassistant.sdk.FfAssistant
import com.ffassistant.sdk.data.ChatRepository
import com.ffassistant.sdk.databinding.ActivityChatBinding
import com.ffassistant.sdk.network.AssistantResult
import com.ffassistant.sdk.network.ChatMessage
import com.ffassistant.sdk.network.Sender
import com.google.android.material.card.MaterialCardView
import kotlinx.coroutines.launch

class ChatActivity : AppCompatActivity() {
    private lateinit var binding: ActivityChatBinding
    private lateinit var repository: ChatRepository
    private val messages = mutableListOf<ChatMessage>()
    private val adapter = MessageAdapter(messages)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChatBinding.inflate(layoutInflater)
        setContentView(binding.root)

        repository = ChatRepository(FfAssistant.context())
        binding.messages.layoutManager = LinearLayoutManager(this)
        binding.messages.adapter = adapter

        val cachedMessages = repository.loadMessages()
        if (cachedMessages.isNotEmpty()) {
            messages.addAll(cachedMessages)
            adapter.notifyDataSetChanged()
        }

        binding.send.setOnClickListener { sendMessage() }
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
            val responseText = when (result) {
                is AssistantResult.Success -> result.value.answer
                is AssistantResult.Failure -> result.error.userMessage
            }

            val assistantMessage = repository.assistantMessage(responseText)
            messages += assistantMessage
            repository.saveMessage(assistantMessage)
            adapter.notifyItemInserted(messages.lastIndex)
            binding.messages.scrollToPosition(messages.lastIndex)
            binding.loading.visibility = View.GONE
            binding.send.isEnabled = true
        }
    }
}

private class MessageAdapter(private val items: List<ChatMessage>) : RecyclerView.Adapter<MessageAdapter.Holder>() {
    class Holder(view: View) : RecyclerView.ViewHolder(view)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): Holder {
        val view = LayoutInflater.from(parent.context).inflate(com.ffassistant.sdk.R.layout.item_message, parent, false)
        return Holder(view)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: Holder, position: Int) {
        val message = items[position]
        val card = holder.itemView as MaterialCardView
        val textView = card.findViewById<TextView>(com.ffassistant.sdk.R.id.messageText)
        textView.text = message.text

        val isUser = message.sender == Sender.USER
        val layoutParams = card.layoutParams as RecyclerView.LayoutParams
        layoutParams.marginStart = if (isUser) 64 else 0
        layoutParams.marginEnd = if (isUser) 0 else 64
        card.layoutParams = layoutParams

        card.setCardBackgroundColor(
            if (isUser) 0xFF1F5EFF.toInt() else 0xFFE9EEF8.toInt()
        )
        textView.setTextColor(if (isUser) 0xFFFFFFFF.toInt() else 0xFF1B1B1B.toInt())
        textView.gravity = if (isUser) Gravity.END else Gravity.START
    }
}