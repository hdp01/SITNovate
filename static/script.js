let conversationState = {
  needsImage: false,
  processingParams: null,
};

// Initialize event listeners
document
  .getElementById("imageInput")
  .addEventListener("change", handleImageUpload);

async function handleSend() {
  const userInput = document.getElementById("userInput");
  const message = userInput.value.trim();

  if (!message) {
    showError("Please enter your request");
    return;
  }

  addMessage(message, "user");
  userInput.value = "";

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        context: conversationState,
      }),
    });

    const data = await response.json();

    if (data.type === "parameters") {
      conversationState.processingParams = data.parameters;
      conversationState.needsImage = true;
      showUploadSection();
      addMessage(data.message, "bot");
    } else {
      addMessage(data.message, "bot");
    }
  } catch (error) {
    showError("Connection error. Please try again.");
  }
}

async function handleImageUpload() {
  const input = document.getElementById("imageInput");
  if (!input.files.length) return;

  showLoading();

  try {
    const formData = new FormData();
    formData.append("image", input.files[0]);
    formData.append(
      "params",
      JSON.stringify(conversationState.processingParams)
    );

    const response = await fetch("/process-image", {
      method: "POST",
      body: formData,
    });

    const result = await response.json();

    if (result.type === "image") {
      displayProcessedImage(result.image, result.format);
      addMessage(result.message, "bot");
      resetConversation();
    } else {
      showError(result.message);
    }
  } catch (error) {
    showError("Image processing failed");
  } finally {
    hideLoading();
  }
}

// Helper functions
function addMessage(text, type) {
  const messagesDiv = document.getElementById("chatMessages");
  const messageDiv = document.createElement("div");
  messageDiv.className = `${type}-message`;
  messageDiv.innerHTML = `<div class="message-content">${text}</div>`;
  messagesDiv.appendChild(messageDiv);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function showUploadSection() {
  document.getElementById("uploadSection").style.display = "block";
}

function resetConversation() {
  conversationState = { needsImage: false, processingParams: null };
  document.getElementById("uploadSection").style.display = "none";
  document.getElementById("imageInput").value = "";
  document.getElementById("fileName").textContent = "";
}

function suggestAction(action) {
  const presets = {
    resize: "Resize for Instagram post (1080x1080)",
    crop: "Crop to focus on the main subject",
    optimize: "Optimize for web usage (70% quality)",
  };
  document.getElementById("userInput").value = presets[action];
}

function displayProcessedImage(imageData, format) {
  const img = document.createElement("img");
  img.className = "processed-image";
  img.src = `data:image/${format};base64,${imageData}`;
  document.getElementById("chatMessages").appendChild(img);
}

function showLoading() {
  const overlay = document.createElement("div");
  overlay.className = "processing-overlay";
  overlay.innerHTML = '<div class="processing-spinner"></div>';
  document.body.appendChild(overlay);
  overlay.style.display = "flex";
}

function hideLoading() {
  document.querySelector(".processing-overlay")?.remove();
}

function showError(message) {
  addMessage(message, "error");
}
