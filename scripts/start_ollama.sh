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

# Pull models from OLLAMA_MODELS environment variable
if [ -n "$OLLAMA_MODELS" ]; then
    IFS=',' read -ra MODELS <<< "$OLLAMA_MODELS"
    for model in "${MODELS[@]}"; do
        echo "Retrieving model: $model..."
        ollama pull "$model"
        echo "Model $model pulled successfully."
        
        echo "Pre-loading model: $model..."
        # Use a simple prompt to force load the model into VRAM
        ollama run "$model" "ok" > /dev/null
        echo "Model $model pre-loaded."
    done
else
    echo "No models specified in OLLAMA_MODELS. Skipping pulls."
fi

echo "All specified models are ready!"

# Wait for Ollama process to finish.
wait $pid
