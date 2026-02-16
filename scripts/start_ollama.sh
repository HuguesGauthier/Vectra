#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &

# Record Process ID.
pid=$!

# Pause for Ollama to accept connections.
sleep 5

echo "🔴 Retrieving bge-m3 model..."
ollama pull bge-m3
echo "🟢 Pulled!"
echo "🔥 Pre-loading bge-m3..."
ollama run bge-m3 ""
echo "🟢 Done!"

echo "🔴 Retrieving mistral model..."
ollama pull mistral
echo "🟢 Pulled!"
echo "🔥 Pre-loading mistral..."
ollama run mistral ""
echo "🟢 Done!"

# Wait for Ollama process to finish.
wait $pid
