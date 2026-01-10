# Frequently Asked Questions

## General

### What is Code Cobra?
Code Cobra is an autonomous multi-agent AI coding system that uses three specialized LLMs working in sequence to generate, correct, and secure code based on natural language specifications.

### What LLMs does it support?
Code Cobra works with any Ollama-compatible model. Recommended models:
- **Model A (Creative)**: `qwen2.5-coder:7b`
- **Model B (Analyst)**: `deepseek-coder-v2:16b`
- **Model C (Adversary)**: `codestral:22b`

### Is an internet connection required?
No. Code Cobra runs entirely locally using Ollama. No external API calls are made.

### What are the system requirements?
- Python 3.8+
- Ollama installed and running
- Sufficient RAM for your chosen models (8GB+ recommended)
- GPU optional but recommended for faster inference

## Installation

### How do I install Code Cobra?
```bash
git clone https://github.com/kase1111-hash/Code_Cobra.git
cd Code_Cobra
./scripts/setup.sh
source venv/bin/activate
```

### How do I install Ollama?
Visit [ollama.ai](https://ollama.ai) and follow installation instructions for your OS. Then pull required models:
```bash
ollama pull qwen2.5-coder:7b
ollama pull deepseek-coder-v2:16b
ollama pull codestral:22b
```

### Can I use Docker?
Yes! Use the provided Docker setup:
```bash
docker-compose up -d
```

## Usage

### How do I run a basic task?
```bash
python autonomous_ensemble.py \
  --spec "Build a REST API for user management" \
  --guide coding_guide.txt \
  --verbose
```

### What are guide files?
Guide files contain step-by-step instructions for the AI to follow. Each line starts with `Step N:` followed by a description:
```
Step 1: Analyze requirements
Step 2: Design architecture
Step 3: Implement core logic
```

### How do I create custom guides?
Create a text file with steps:
```
Step 1: Your first instruction
Step 2: Your second instruction
...
```
Save as `my_guide.txt` and use with `--guide my_guide.txt`

### How do I chain multiple guides?
```bash
python autonomous_ensemble.py \
  --spec "My project" \
  --chain coding_guide.txt testing_guide.txt deploy_guide.txt
```

### How do I resume an interrupted workflow?
Use checkpointing:
```bash
# Start with checkpoint
python autonomous_ensemble.py --spec "..." --checkpoint progress.json

# Resume later
python autonomous_ensemble.py --spec "..." --resume progress.json
```

## Configuration

### How do I change the models?
Create a JSON config file:
```json
{
  "model_a": "llama2:13b",
  "model_b": "codellama:7b",
  "model_c": "mistral:7b"
}
```
Run with: `--config my_config.json`

### How do I adjust temperature settings?
In your config file:
```json
{
  "temp_creative": 0.9,
  "temp_analytical": 0.2,
  "temp_adversarial": 0.6
}
```

### What does max_iterations control?
It limits how many times Model B and Model C iterate on their output. Default is 3. Increase for more thorough refinement.

## Troubleshooting

### "Connection refused" error
Ollama is not running. Start it:
```bash
ollama serve
```

### "Model not found" error
Pull the required model:
```bash
ollama pull <model-name>
```

### Output is empty or low quality
- Increase `max_tokens` in config
- Try different models
- Make your specification more detailed
- Use more specific guide steps

### Process is too slow
- Use smaller models (7B instead of 22B)
- Reduce `max_iterations`
- Use GPU acceleration with Ollama
- Reduce the number of guide steps

### Memory issues
- Use smaller models
- Close other applications
- Increase system swap space

## Advanced

### Can I add custom processing between models?
Yes, use hooks:
```python
from autonomous_ensemble import WorkflowEngine, PipelineHooks

def my_hook(text):
    return text.replace("TODO", "COMPLETED")

hooks = PipelineHooks(post_draft=my_hook)
engine = WorkflowEngine(config, hooks=hooks)
```

### How do I integrate with CI/CD?
Use the `--dry-run` flag to validate guides without running models:
```yaml
- name: Validate guides
  run: python autonomous_ensemble.py --dry-run --guide coding_guide.txt
```

### Can I use this for production code?
Code Cobra is designed for code generation assistance. Always review output before using in production:
1. Run your standard test suite
2. Perform code review
3. Run security scanning tools
4. Test in staging environment first
