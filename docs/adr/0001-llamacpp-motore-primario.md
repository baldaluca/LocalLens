# llama.cpp come motore primario, non stack Python/PyTorch

Le build torch+CUDA/ROCm restringono nel tempo le architetture supportate (già successo
con Maxwell/Pascal) e legano la compatibilità alla combinazione esatta installata.
llama-server espone backend nativi intercambiabili (CUDA/HIP/Vulkan/CPU) dietro la stessa
API OpenAI-compatibile, con binari pinnati per backend e selezione a runtime.
