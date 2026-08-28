package com.ffassistant.sdk.ui

import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.View
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
        messages += cachedMessages
        adapter.notifyItemRangeInserted(0, cachedMessages.size)
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
            when (val result = repository.send(text)) {
                is AssistantResult.Success -> repository.assistantMessage(result.value.answer)
                    .also { messages += it; repository.saveMessage(it) }
                is AssistantResult.Failure -> repository.assistantMessage(result.error.userMessage)
                    .also { messages += it; repository.saveMessage(it) }
            }
            adapter.notifyItemInserted(messages.lastIndex)
            binding.messages.scrollToPosition(messages.lastIndex)
            binding.loading.visibility = View.GONE
            binding.send.isEnabled = true
        }
    }
}

private class MessageAdapter(private val items: List<ChatMessage>) : RecyclerView.Adapter<MessageAdapter.Holder>() {
    class Holder(view: View) : RecyclerView.ViewHolder(view)
    override fun onCreateViewHolder(parent: android.view.ViewGroup, viewType: Int) =
        Holder(android.view.LayoutInflater.from(parent.context).inflate(com.ffassistant.sdk.R.layout.item_message, parent, false))
    override fun getItemCount() = items.size
    override fun onBindViewHolder(holder: Holder, position: Int) {
        val view = holder.itemView as android.widget.TextView
        val message = items[position]
        view.text = message.text
        view.gravity = if (message.sender == Sender.USER) Gravity.END else Gravity.START
        view.setTextColor(Color.DKGRAY)
    }
}