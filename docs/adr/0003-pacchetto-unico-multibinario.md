# Pacchetto unico per OS con multi-binario e selezione a runtime

Invece di installer separati per backend, ogni pacchetto OS include tutti i binari
llama-server pertinenti (CUDA, HIP solo Linux, Vulkan, CPU). La stessa logica di
rilevamento di RF3 sceglie il binario, evitando l'errore di pacchetto sbagliato e
adattandosi a cambi hardware senza reinstallazione.
