from langchain_community.chat_models import ChatLlamaCpp
from pathlib import Path
path = Path("E:/SIH_26/SERVER/Classfication/Models/LLM/Qwen3.5-4B-Q4_K_M.gguf")
llm = ChatLlamaCpp( model_path=str(path),
    n_ctx=4000,
    n_gpu_layers=0,
    verbose=False,
    max_tokens=5000)

prompt = """
the given statement is saying right or not answer in one word 

statement report - 
{
  "report_id": "SIF-b98d9e4e5a64",
  "input": {
    "text": "AC ka remote kahrab ho gya hia naya lana hoga",
    "chars": 45
  },
  "meta": {
    "site": null,
    "date": null,
    "activity": null,
    "department": null,
    "language_detected": "english",
    "statement_type": "condition_only"
  },
  "verdict": {
    "label": "EXPOSURE",
    "confidence": 0.48,
    "conformal_set": [
      "EXPOSURE",
      "LOW_ENERGY"
    ],
    "route": "slow_lane",
    "layers_agreed": [
      "rules",
      "gliner"
    ],
    "llm_invoked": false,
    "decision_path": "high_energy=True AND energy_released=False AND control_present=False -> EXPOSURE (no barrier, not released yet)",
    "head_verdict": "LOW_ENERGY",
    "head_confidence": 0.2875
  },
  "eei_facts": {
    "high_energy_present": {
      "value": true,
      "span": "AC",
      "span_start": 0,
      "span_end": 2,
      "source": "gliner"
    },
    "energy_released": {
      "value": false,
      "span": null,
      "span_start": null,
      "span_end": null,
      "source": "default_no_release_stated"
    },
    "serious_injury": {
      "value": false,
      "span": null,
      "span_start": null,
      "span_end": null,
      "source": "default_no_injury_stated"
    },
    "direct_control_present": {
      "value": false,
      "span": null,
      "span_start": null,
      "span_end": null,
      "source": "default_no_control_stated"
    }
  },
  "energy": {
    "type": null,
    "estimate_j": null,
    "range_j": null,
    "basis": null,
    "formula": null,
    "inputs": {},
    "threshold_j": null,
    "gate": "UNKNOWN"
  },
  "safety_knowledge": {
    "hazard": null,
    "barrier": null,
    "barrier_failure_mode": "not_established",
    "lsr": [],
    "potential_consequence": null,
    "precursor_cluster": null
  },
  "spans": [
    {
      "role": "energy_cue",
      "text": "AC",
      "start": 0,
      "end": 2,
      "source": "gliner",
      "score": 0.635
    }
  ],
  "traps_checked": {
    "negation_detected": false,
    "negation_scope": null,
    "note": null
  },
  "uc_ua": {
    "labels": [
      "UC"
    ],
    "unsafe_act": false,
    "unsafe_condition": true,
    "confidence": 0.35,
    "act_cues": [],
    "condition_cues": [],
    "actor": null,
    "passive_victim": false,
    "basis": "rules"
  },
  "scope": {
    "reject": false,
    "p_out_of_scope": 0.6406,
    "veto": null,
    "reason": "in scope (p_out=0.64 <= 0.95)"
  },
  "review": {
    "required": true,
    "reason": "confidence 0.48 below review threshold",
    "human_reviewed": false,
    "reviewer_verdict": null
  },
  "provenance": {
    "pipeline_version": "0.5.0",
    "package_version": "0.5.0",
    "models": {
      "gliner": "gliner_sif",
      "heads": "lsr,prefilter,statement_type,verdict",
      "llm": null
    },
    "head_predictions": {
      "lsr": {
        "label": "0",
        "confidence": 0.4949
      },
      "prefilter": {
        "label": "0",
        "confidence": 0.7139
      },
      "statement_type": {
        "label": "condition_only",
        "confidence": 0.3749
      },
      "verdict": {
        "label": "LOW_ENERGY",
        "confidence": 0.2875
      }
    },
    "processed_at": "2026-09-11T18:51:15+05:30"
  }
}

"""
chat= llm.invoke(prompt=prompt)
print(chat.content)