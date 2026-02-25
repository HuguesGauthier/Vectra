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

# Pull models from MODELS_TO_PULL environment variable
if [ -n "$MODELS_TO_PULL" ]; then
    IFS=',' read -ra MODELS <<< "$MODELS_TO_PULL"
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

# Create a flag file to signal healthcheck that we are ready
touch /tmp/ready

echo "All specified models are ready!"

# Wait for Ollama process to finish.
wait $pid
