# Sanskrit Glossary for the Vākya Protocol
## संस्कृत शब्दकोश

This glossary maps every Sanskrit term used in the Vākya protocol to its meaning.
Understanding these terms helps you read wire messages and protocol code naturally.

---

## Core Terms

| Sanskrit | Transliteration | Pronunciation | English | Used For |
|----------|----------------|---------------|---------|----------|
| वाक्य | Vākya | VAA-kya | Expression, Sentence | Protocol name; a message |
| संवाद | Saṃvāda | sam-VAA-da | Dialogue, Conversation | Conversation thread ID |
| सन्देश | Sandeśa | san-DAY-sha | Message | Wire format payload field |
| प्रेषक | Preṣaka | PRAY-sha-ka | Sender | Sender field |
| प्रापक | Prāpaka | PRAA-pa-ka | Receiver | Recipient field |
| समय | Samaya | sa-MA-ya | Time | Timestamp field |
| प्रकार | Prakāra | pra-KAA-ra | Type, Kind | Message type field |
| विषय | Viṣaya | vi-SHA-ya | Subject, Topic | Topic/subject field |
| शरीर | Śarīra | sha-REE-ra | Body | Message body/content |
| सन्दर्भ | Sandarbha | san-DAR-bha | Context, Reference | Message metadata |
| प्रमाण | Pramāṇa | pra-MAA-na | Proof, Validation | Integrity hash |

## Agent Terms

| Sanskrit | Transliteration | Pronunciation | English | Used For |
|----------|----------------|---------------|---------|----------|
| दूत | Dūta | DOO-ta | Messenger, Ambassador | AI agent identity |
| सभा | Sabhā | sa-BHAA | Assembly, Council | Group of AIs; router |
| सूत्र | Sūtra | SOO-tra | Thread, String | Communication channel |
| भाषा | Bhāṣā | BHAA-shaa | Language | Supported languages |

## Role Terms

| Sanskrit | Transliteration | Pronunciation | English | Used For |
|----------|----------------|---------------|---------|----------|
| नेता | Netā | NAY-taa | Leader | Coordinator role |
| कर्तृ | Kartṛ | kar-TRI | Doer, Maker | Worker/executor role |
| समीक्षक | Samīkṣaka | sa-MEEK-sha-ka | Examiner | Reviewer role |
| परीक्षक | Parīkṣaka | pa-REEK-sha-ka | Tester | Validator role |
| मन्त्री | Mantrī | man-TREE | Minister, Advisor | Advisor role |
| श्रोतृ | Śrotṛ | SHRO-tri | Listener | Observer role |
| मध्यस्थ | Madhyastha | ma-dhya-STHA | Mediator | Mediator role |

## Message Type Terms

| Sanskrit | Transliteration | Pronunciation | English | Used For |
|----------|----------------|---------------|---------|----------|
| प्रश्न | Praśna | PRASH-na | Question | Question message |
| उत्तर | Uttara | UT-ta-ra | Answer | Response message |
| कार्य | Kārya | KAAR-ya | Task, Duty | Task assignment |
| प्रतिवेदन | Prativedana | pra-ti-VAY-da-na | Report | Status report |
| स्वीकृति | Svīkṛti | svee-KRI-ti | Acceptance | Acknowledgment |
| निर्णय | Nirṇaya | nir-NA-ya | Decision | Decision message |
| विवाद | Vivāda | vi-VAA-da | Dispute | Disagreement |
| अभिवादन | Abhivādana | a-bhi-VAA-da-na | Greeting | Handshake |
| विसर्जन | Visarjana | vi-SAR-ja-na | Release | Farewell/disconnect |

## Task Terms

| Sanskrit | Transliteration | Pronunciation | English | Used For |
|----------|----------------|---------------|---------|----------|
| स्थिति | Sthiti | STHI-ti | State, Status | Task status |
| प्रवृत्ति | Pravṛtti | pra-VRIT-ti | Progress, Activity | Progress value |
| विवरण | Vivaraṇa | vi-va-RA-na | Description | Status description |
| फल | Phala | PHA-la | Fruit, Result | Task result |

## Status Terms

| Sanskrit | Transliteration | English |
|----------|----------------|---------|
| प्रतीक्षा | Pratīkṣā | Pending / Waiting |
| सक्रिय | Sakriya | Active / In-progress |
| सम्पूर्ण | Sampūrṇa | Complete |
| विफल | Viphala | Failed |
| निरस्थ | Nirastha | Cancelled |
| अवरोधित | Avarodhita | Blocked |

## Priority Terms

| Sanskrit | Transliteration | English |
|----------|----------------|---------|
| अत्यावश्यक | Atyāvaśyaka | Critical / Urgent |
| उच्च | Ucca | High |
| मध्यम | Madhyama | Medium |
| निम्न | Nimna | Low |

## Other Terms

| Sanskrit | Transliteration | English | Used For |
|----------|----------------|---------|----------|
| इतिहास | Itihāsa | History | Message history |
| नमस्ते | Namaste | Greetings | Welcome messages |
| मानव | Mānava | Human | Human observer |
| दर्शक | Darśaka | Viewer | Monitor/viewer |
| ॐ | Oṃ | Sacred syllable | Used in documentation |

## Bridge Terms (Cross-IDE)

| Sanskrit | Transliteration | Pronunciation | English | Used For |
|----------|----------------|---------------|---------|----------|
| सेतु | Setu | SAY-tu | Bridge | Cross-IDE bridge daemon |
| खोज | Khoj | KHOJ | Search, Discovery | IDE agent discovery service |
| योजक | Yojaka | YO-ja-ka | Connector, Joiner | IDE-to-bridge adapter |
| द्वार | Dwār | DWAAR | Gate, Door | Transport protocol gateway |

---

## Why Sanskrit?

1. **Neutrality**: Sanskrit belongs to no single modern nation — it's a shared heritage
2. **Precision**: Sanskrit has extraordinarily precise grammatical terminology
3. **AI-friendly**: Short, unambiguous terms that tokenize well for LLMs
4. **Universal**: Sanskrit roots appear across Indo-European languages
5. **Beauty**: The protocol becomes more meaningful and elegant

---

*सर्वे भवन्तु सुखिनः — May all beings be happy*
