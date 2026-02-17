#!/bin/bash

# Start Ollama in the background.
/bin/ollama serve &

# Record Process ID.
pid=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama service to start..."
until ollama list > /dev/null 2>&1; do
    sleep 1
done
echo "Ollama service is ready!"

echo "Retrieving model: bge-m3..."
ollama pull bge-m3
echo "Model bge-m3 pulled successfully."

echo "Retrieving model: mistral..."
ollama pull mistral
echo "Model mistral pulled successfully."

echo "Pre-loading model: mistral..."
ollama run mistral "say ok" > /dev/null
echo "Model mistral pre-loaded."

echo "Pre-loading model: bge-m3..."
# For embedding models, we can use 'run' with a dummy input as well to force load into VRAM
ollama run bge-m3 "warmup" > /dev/null
echo "Model bge-m3 pre-loaded."

# Wait for Ollama process to finish.
wait $pid
