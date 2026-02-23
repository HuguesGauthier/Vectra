::: mermaid
flowchart TD
MSG([Message envoyé]) --> CS[ChatService]

    CS --> INIT["🔵 initialization\n⏱ Oui | 🪙 Non"]
    CS --> HL["🔵 history_loading\n⏱ Oui | 🪙 Non"]
    CS --> CL["🔵 cache_lookup\n⏱ Oui | 🪙 Non"]
    CS --> UP["🔵 user_persistence\n⏱ Oui | 🪙 Non"]

    CL -->|Hit| CH["🟢 cache_hit\n⏱ Oui | 🪙 Non"]
    CL -->|Miss| CM["🟠 cache_miss\n⏱ Non | 🪙 Non"]

    CH --> DONE
    CM --> PROC

    UP --> PROC{Quel processeur?}

    PROC -->|RAG| RAG_PROC
    PROC -->|Agentic Router| AGENT
    PROC -->|CSV| CSV_PROC

    subgraph RAG_PROC["Pipeline RAG Standard"]
        R_RET["🔵 retrieval\n⏱ Oui | 🪙 Non"]
        R_SYN["🔵 synthesis\n⏱ Oui | 🪙 Oui"]
        R_RET --> R_SYN
    end

    subgraph AGENT["Pipeline Agentic Router"]
        direction TB
        ROUTER["🔵 router (parent)\n⏱ Total | 🪙 Non"]

        subgraph ROUTER_STEPS["Sous-étapes Router"]
            QR["🔵 query_rewrite\n⏱ Oui | 🪙 ✅ Oui"]
            RP["🔵 router_processing\n⏱ Oui | 🪙 Non"]
            QE["🔵 query_execution\n⏱ Oui | 🪙 Non"]

            subgraph LLM_LOOP["Boucle LLM ← callbacks.py"]
                RS["🔵 router_selection\n⏱ ✅ caché | 🪙 Oui"]

                FUNC_CALL["⚡ FUNCTION_CALL\n← IsolatedQueryEngine\nContextVar.set(tool_name)\n🚫 masqué UI"]

                RETR["🔵 retrieval (documents_X)\n⏱ Oui | 🪙 Non\nLabel ← ContextVar.get()\nasync-safe vs gather()"]

                RR["🔵 router_reasoning\n(callbacks)\n🚫 masqué UI\n— remplacé par ROUTER_SYNTHESIS"]

                RS -->|"LLMMultiSelector\n(N tâches en parallèle)"| FUNC_CALL
                FUNC_CALL --> RETR
                RETR --> RR
                RR -->|multi-hop| FUNC_CALL
            end

            RSYNTH["🔵 router_synthesis\n⏱ ✅ Oui (explicite) | 🪙 Oui\n← AgenticProcessor"]
            RR --> RSYNTH
        end

        ROUTER --> QR --> RP --> QE --> RS
    end

    subgraph CSV_PROC["Pipeline CSV"]
        CSV_RET["🔵 csv_schema_retrieval\n⏱ Oui | 🪙 Non"]
        CSV_SYN["🔵 csv_synthesis\n⏱ Oui | 🪙 Oui"]
        CSV_RET --> CSV_SYN
    end

    RAG_PROC --> STREAM["🔵 streaming\n⏱ Oui | 🪙 Non"]
    AGENT --> VIZ["🔵 visualization_analysis\n⏱ Oui | 🪙 Oui"]
    CSV_PROC --> STREAM

    VIZ --> STREAM
    STREAM --> TREND["🔵 trending\n⏱ Oui | 🪙 Non"]
    TREND --> AP["🔵 assistant_persistence\n⏱ Oui | 🪙 Non"]
    AP --> CU["🔵 cache_update (async)\n⏱ Oui | 🪙 Non"]
    CU --> DONE["🟢 completed\n⏱ Total | 🪙 Total"]

:::
