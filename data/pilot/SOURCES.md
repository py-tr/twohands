# Pilot ("spike") files copied into this repo

The 43-form tally-sheet pilot and the 40-sheet rainfall-ledger pilot were run in sibling working folders
(`../spikes/tally-witness`, `../spikes/ledger-rescue`: the builder's local folders, outside this repo and not
published; their write-ups are copied in [`docs/sources/`](../../docs/sources/README.md)). The files the code reads were copied here on
2026-10-16, byte for byte, so the repo is self-contained. JSON and CSV only: no images (the pilot's unmasked acta
images and the ledger sheet scans stay out), no code. Checked before copying: the tally files hold PREP / Computos
numeric rows, the public PREP image URL, sample stratum and model reads of the 22 numeric fields (no names; the
PREP `OBSERVACIONES` field is blank for all 43); the ledger files hold station names, years and rainfall values
(Rainfall Rescue, CC-BY-4.0, github.com/ed-hawkins/rainfall-rescue).

Not copied: the spikes' README.md files, which the docs still cite for context numbers (counts over the PREP CSV,
press quotes), and the spikes' Python scripts; `ledger/build.py` carries the ledger scorer's logic.

Readers: `twohands/__init__.py` (`PILOT_DATA`, `PILOT_RESULTS`), `twohands/sample.py` (`SPIKE_SAMPLE`),
`app/build.py`, `ledger/build.py`, `scripts/consistency_43.py`, `scripts/verify_spike.py`.


## Single files

| In repo | Source | sha256 |
|---|---|---|
| `data/pilot/tally-witness/sample.json` | `../spikes/tally-witness/data/sample.json` | `ca936111d0651d63369c0ecfdd2ded8b88f1321f717dc039336b1bd07ba03449` |
| `data/pilot/tally-witness/truth_rows.json` | `../spikes/tally-witness/data/truth_rows.json` | `cf3f79adc2c93b22820939693707f6f62f3e4210743d78da3113ac02eb36867a` |
| `data/pilot/tally-witness/adjudicate.json` | `../spikes/tally-witness/adjudicate.json` | `3a52395bf73b430afba27eef6a7dba152c6409aeb34ae35c616da19e5a66e7c7` |
| `data/pilot/tally-witness/scores_gemma_v2.json` | `../spikes/tally-witness/scores_gemma_v2.json` | `1e18f90639f91c607101f96512e3a942e2ed72cad3246e8670fcc1bb144981f5` |
| `data/pilot/ledger-rescue/picked.json` | `../spikes/ledger-rescue/data/picked.json` | `20661b235ab2aa00df6a58ecbe336f351205606f19b1c04d09fe8f31506fb431` |
| `data/pilot/ledger-rescue/sheets40.json` | `../spikes/ledger-rescue/data/sheets40.json` | `2a7fcea7b9f546bff878b9e4262229d338e18da9571dfa3050aae0e21a99eb2a` |
| `data/pilot/ledger-rescue/scores.json` | `../spikes/ledger-rescue/scores.json` | `4bfef79e06f0072b94b170a19848511eb2dd913ff3112a3741a02d063359c59b` |

## Directories (one row per file)

### `data/pilot/ledger-rescue/csv/*.csv` (40 files, the volunteers' transcriptions of the 40 sheets)

Source: `../spikes/ledger-rescue/data/csv/*.csv`, same file names.

| File | sha256 |
|---|---|
| `ARDNAMURCHAN-LIGHTHOUSE__ERROR_TYRain_1920-1930_31_pt1-page-142.csv` | `f59647b9f556b17f9d2f466c246246d7f5f3b5243d5ccc3ecb7c57aaee45f89d` |
| `ARDNAMURCHAN-LIGHTHOUSE__TYRain_1850-1859_H_pt1-page-164.csv` | `1e2455032678fa87ac4f2a3d1f1fde56bf50ce3e4a6a122bb3c0f9059b4e6444` |
| `ARDNAMURCHAN-LIGHTHOUSE__TYRain_1860-1869_07_pt2-page-057.csv` | `38c660edaef19ae70fb9d4b271e22f411785bf231ba222442496d7dc54fe60ea` |
| `ARDNAMURCHAN-LIGHTHOUSE__TYRain_1870-1879_11_pt3-page-059.csv` | `85076ddb29f19eee3588d5532c7c3439eeba97b5a3adce05774d3b16b620131c` |
| `ARDNAMURCHAN-LIGHTHOUSE__TYRain_1880-1889_15_pt1-page-042.csv` | `4849cae26aabf6c3bd17b216a7c42a58e5524969adc9faa430853da272a291b8` |
| `ARDNAMURCHAN-LIGHTHOUSE__TYRain_1890-1899_24_pt1-page-143.csv` | `e38c58c69d004fe885b05421a9889673b5e7b263789c44c6210c8da9cea5e24f` |
| `ARDNAMURCHAN-LIGHTHOUSE__TYRain_1900-1909_28_pt1-page-156.csv` | `0582d92204c81b53a02abef94b671eb80f1ca485e2f6a14ea43fc69667691d2a` |
| `ARDNAMURCHAN-LIGHTHOUSE__TYRain_1910-1919_27_pt1-page-003.csv` | `0dc6a05c5443d0d10522f935862a27ca3360572afa9a9804d2d49d23392ae455` |
| `ARDNAMURCHAN-LIGHTHOUSE__TYRain_1951-1960_27_pt1-page-168.csv` | `c214c922f190c78da38b180f042223cd35d4a19285053035a7a222e24efc1f54` |
| `BALCOMBE-GABLES__ERROR_TYRain_1931-1940_04_pt1-page-207.csv` | `3bd3f52c2a288eb083ad3dc3294c0d99bd8188da792a50f8f597e0423ecc7a91` |
| `BALCOMBE-GABLES__TYRain_1860-1869_01_pt2-page-145.csv` | `3eca163b2aeb3b540169ea76459fd949b1f4853f7eb5156b50849b2c75481cc3` |
| `BALCOMBE-GABLES__TYRain_1870-1879_02_pt1-page-103.csv` | `f0db18445a73b455022fd4846d6ba1e207cdc2b7c5d10b1a2c433e6baa5b9d91` |
| `BALCOMBE-GABLES__TYRain_1880-1889_02_pt2-page-065.csv` | `f298924f6314a47c075d4ad05144663784f5d2d99fb92946c70ac21ec745079a` |
| `BALCOMBE-GABLES__TYRain_1890-1899_04_pt1-page-091.csv` | `4b57016b42cfcddc71715944533ac00ed88f5a74e1c3cf829bdc8e653cdcb648` |
| `BALCOMBE-GABLES__TYRain_1900-1909_04_pt1-page-110.csv` | `669dcb8553079e6f4833ed249b79c5a33f47afb3ff5e945f0aad1c1eafaa854b` |
| `BALCOMBE-GABLES__TYRain_1910-1919_04_pt1-page-150.csv` | `91b48c0d61122c9591208900e0c1c9a9d2aff4b846d2345e42664de13dd91ac8` |
| `BALCOMBE-GABLES__TYRain_1920-1930_04_pt1-page-166.csv` | `3e1122ca431e56fa9ae6d631f393a96f4f49ee37c8582379abc2ab8ed3bea19d` |
| `BALCOMBE-HIGHLEY-MANOR__TYRain_1890-1899_04_pt1-page-090.csv` | `64d9271d068dd0ad46b2ef7b71cbb33bc1b20e87911d18cad8c18bc9a742c305` |
| `BALCOMBE-HIGHLEY-MANOR__TYRain_1900-1909_04_pt1-page-109.csv` | `dc47700d15ed19822a7175cc8a0b5e06a871c5b8c6b66b82c81a568b93eb94c8` |
| `BALCOMBE-HIGHLEY-MANOR__TYRain_1910-1919_04_pt1-page-153.csv` | `2dc751cf914cea1b84e48d7d68bd0214e8de212c9b1e3e843a511ecae9ceb134` |
| `BALCOMBE-HIGHLEY-MANOR__TYRain_1920-1930_04_pt1-page-169.csv` | `60a3f4e519dc34de2f9088db4d7ca3f5ee1f4c9f8d620f62585a0cc83a688587` |
| `BALCOMBE-HIGHLEY-MANOR__TYRain_1931-1940_04_pt1-page-210.csv` | `556d7915844b7f91cfddf38d6266bda9d3c860f7de60f60c5ebc432f9cc99ab9` |
| `BALCOMBE-HIGHLEY-MANOR__TYRain_1941-1950_04_pt1-page-153.csv` | `bd4a5936dbb27648c0425454fececeae53f7be4b27b1248591f8b1933bfab15c` |
| `BALCOMBE-HIGHLEY-MANOR__TYRain_1951-1960_03_pt1-page-112.csv` | `a520c31bd5bae6485001c8feef11d477206a57fe2c86cf456d71ab9ecbc2261a` |
| `BARKBY-HALL__TYRain_1870-1879_06_pt2-page-105.csv` | `651a03c523ec402009fc38a4d257a47c39e24ef4b027f29b495aed710b9e89b9` |
| `BARKBY-HALL__TYRain_1880-1889_07_pt5-page-021.csv` | `ae2fe6694a8a0875b599a9b6251a9a8ad3f42ff5f2faa31e4e734fd71b9e955a` |
| `BARKBY-HALL__TYRain_1890-1899_13_pt1-page-078.csv` | `11b605d41708b4255fa5516682d2b8159a78d7f93a3d48a9f65de5c2d7ac8e68` |
| `BARKBY-HALL__TYRain_1900-1909_17_pt1-page-031.csv` | `a7cc7f1ba3eb3a511a40d784bbadb0bba989da3852112689f5e526ef9483122b` |
| `BARKBY-HALL__TYRain_1910-1919_15_pt1-page-287.csv` | `ef9718942c26d567571709320a80d0bab85bf79712ec4723a57f44d20d6b5567` |
| `BARKBY-HALL__TYRain_1920-1930_16_pt1-page-157.csv` | `9110c7bc6f3064d043648f5f338498bbe9310260e6364d50f98e8141141cb83b` |
| `BARKBY-HALL__TYRain_1931-1940_15_pt1-page-039.csv` | `61912f64023edfa19bc52f6d9ab68ee6022d11de4d0af39d1ff2e28a1335d7e1` |
| `BARKBY-HALL__TYRain_1941-1950_17_pt1-page-126.csv` | `314459ef8f20efffe64a2fc4668de3c30b055588daf093741c9f5c190f615362` |
| `BARKBY-HALL__TYRain_1951-1960_15_pt1-page-128.csv` | `ac7a693da6f659368ff6ae9b8d698a8d39a5b2877d4c1a26f8600ca59241fb51` |
| `BARROWFORD-RES__ERROR_TYRain_1920-1930_20_pt1-page-152.csv` | `ca1f49d2e0325bf905209e11bc793341d930ea8143b346b6c5a449388d562714` |
| `BARROWFORD-RES__ERROR_TYRain_1951-1960_18_pt1-page-063.csv` | `d2adcb9b17ced5fde0bd32e627c6ad86a81cde67bacec5792177c06e7c64228d` |
| `BARROWFORD-RES__TYRain_1890-1899_15_pt1-page-051.csv` | `a2d7a6cb04575778c9924ea14339943f1af10ca15e1d5fc51628bfa29593b05d` |
| `BARROWFORD-RES__TYRain_1900-1909_19_pt1-page-180.csv` | `98ca4a070f08c97501df1c69dd5b8b91f5a3abf5bfc59654067265eb5a21aff0` |
| `BARROWFORD-RES__TYRain_1910-1919_18_pt1-page-152.csv` | `b609f663620bb9ba38b7a111abc339d7e7fcf7703a2caeac817ce7c8a2038507` |
| `BARROWFORD-RES__TYRain_1931-1940_17_pt1-page-254.csv` | `9d93e9775aa9ce1107e61a863c0c88193c765e5e757b52199b66ce55b7d01a70` |
| `BARROWFORD-RES__TYRain_1941-1950_20_pt1-page-069.csv` | `ed9b10c5464adde569af2b1a7231d899afed3707a0c2feca3b139a1752d5f1ad` |

### `results/pilot/tally-witness/results_v2/*.json` (43 files, Gemma-4-31B-IT, page + 4 tiles (spike v2))

Source: `../spikes/tally-witness/results_v2/*.json`, same file names.

| File | sha256 |
|---|---|
| `gemma__010441C0100.json` | `624b66ad5225cda0efa8abccc7ffced63c2e74e3a9efa66e81af837abf85e657` |
| `gemma__010445C0100.json` | `53889f1c80598594ba1cb9f79be541190f34018b40ef7e9cc2738fd080c27704` |
| `gemma__010452B0100.json` | `682663a74d617599847668d28d32b19f1ad75b15548616054baae3963b3d813c` |
| `gemma__010474B0100.json` | `d966b8f681cedf6ccf0edddc59b170f79a81b56421d924d6c4721747787b7c73` |
| `gemma__070159C0300.json` | `f6968ea63ecb47fdfd566b3ecf8fbee79a0ad91d10ddc6c79bed87f4e28034ef` |
| `gemma__070332E0100.json` | `8cb2ebf81262783d8cfc5aee7f1fc305f5e550252fdd26fb5d3a3ed7daf6fb58` |
| `gemma__070394C0100.json` | `176fa06ccd2d3735d3539c59a1e2b2a7a81b8c392b623b2b2580ddbb64585476` |
| `gemma__072055C0300.json` | `ab6947f28806a34d19edead464ef8695bd2478125ee7ec708ccbba4fed28ed9f` |
| `gemma__093954C0200.json` | `831ce964dd9c720c5710ec08069f1a2bcb2edfe200c30a7d4bf44c881f90b942` |
| `gemma__095566C0300.json` | `9f4b0b0658d8641395bd9fba932793440c58331681d0dd1ec4f3775cd7c97aee` |
| `gemma__120293C0100.json` | `94ef123f0e647519e98fd3d8b4af4aae7e8b77caf9dfa2a991d76d890f26320f` |
| `gemma__120295C0300.json` | `689e739b432ffc65ecf54c451bf0e9df976b52daa2f57484b57e7c351dc5de91` |
| `gemma__120301C0400.json` | `ca28000c14e1b761610b812a5f145baad88eb80169e17e643741eca1f2537eb6` |
| `gemma__120306C0900.json` | `9ae990e423199eb975388d7a4c502a224014c1b5054adb0f1bfbd091aca11de2` |
| `gemma__122837B0100.json` | `a917d2a67d9dff3a3c09614512ee5cbc9c9a4f7f580631c889eca39654dfa517` |
| `gemma__122838C0100.json` | `8981dd259d2718ee128ef3da5fffed14521de70ccd72652d2564caee27e34c9a` |
| `gemma__141097C0100.json` | `f24c94a3fb6b0360e3c01da0a8852d047d12abb7a98086ab09fa47a7d3b54704` |
| `gemma__151794C0200.json` | `5816f60201359d094d0a3c4a082991c1d3574212baba77ef806562af09c2b54e` |
| `gemma__151806B0100.json` | `fde2b52dd24e2ac96ca0cd4d6e8f9c64dade588ed2a4c43cb409b46e3f3c5c2f` |
| `gemma__156034C0100.json` | `3ca0fd2b6faedf853417071e6661a49e8770874957db653cef691b5714f7e9be` |
| `gemma__156044B0100.json` | `5cc1cee808ff6aa93059c79f1098a414add45ce1abcaeed8042edd813f3e535f` |
| `gemma__156723B0100.json` | `5d6301158ca877b51509f553170608e749944e9e8d8b81f4bbc154a64db19992` |
| `gemma__191790C0100.json` | `6606cb097d9acd40efb6d6390a411f2e0a1c58a7cb5c7d7b11067d113a3d5320` |
| `gemma__200144B0100.json` | `58be757ac772e52c544d1b22d4affcc8bb3111cb4efee96cc6a9009d2019342e` |
| `gemma__200742B0100.json` | `06ea6a1fac3961790b92cc60b2b0642437d178a0924458a3e6f0fec583714002` |
| `gemma__201280B0100.json` | `df473b19e16057acad811dd4aa52bbe9de897a37a1430e1c79cbb0191b5d6a89` |
| `gemma__201717C0100.json` | `6b1ed92640bdab0600e390a4740105bc2de758222ea23178f5ca1a14177d26e0` |
| `gemma__201720E0100.json` | `d434773165b26d41b58681733f437a6e0369150f331975fc101f399b4483bd77` |
| `gemma__201791B0100.json` | `bb820d0516426d62c31f7ea9bd0029dbacf0353afadded2942a650eaedfba802` |
| `gemma__202156B0100.json` | `f10ed422b90db01b13721f925e510274df9e77f56c89e13da2221c29e52e24cc` |
| `gemma__202338B0100.json` | `c177b962926a723abcd38e9ad920ab1a4d949a90389eeae4a24bb2aa5add3a40` |
| `gemma__202451B0100.json` | `dd167362d62a6e47d721c978eba496ee3d4e574f9a2e39ae99e789d827bbd0d2` |
| `gemma__211294C0100.json` | `a2cebff69352a92eefdfa847404f779f79bb2e3a4dde26a6826e4979cc4b49e8` |
| `gemma__211298B0100.json` | `6a4626e24c19b6cda677a3a3c08e5735639581de5182132c8f0809ad4a6b415d` |
| `gemma__211420C0400.json` | `aeb66a210486d37d83676af05cab7f7ba2d457700a96efbf4dd437a6fc74419d` |
| `gemma__300449C0100.json` | `bef8b9bf23f0e720c74fa788873b28f7fdfb24879128280131763f4d39df448b` |
| `gemma__302296C0200.json` | `dfa0c01b558d912ffb039f360f39e66d9fcd6928fb0c40e009cef11afd6b37e4` |
| `gemma__302307C0100.json` | `e8eaff2c7ecccb04f5a58845db374af59a96126c633e3ee18687de3cb275bf5a` |
| `gemma__302539C0100.json` | `b2e3c2aca55fb6413c54bb0ed49e91182b0e0402c61912cdd133b670f1ceb7ab` |
| `gemma__302541B0100.json` | `59b532e815526774c36bc45a406b41914c1cb6f0df239ddd567dcb34a32e5d84` |
| `gemma__304052B0100.json` | `4c3b9f7f15563796347cecd749845f3be42931d4dea8d8cd4cd2b12d833b4267` |
| `gemma__304069B0100.json` | `77f591057f0d5b6081c30fefb846a9a3cf58f570d0abbacf52aa46af5870f377` |
| `gemma__304968C0100.json` | `384094335e5c098d40e8290ad1eb5ba9fb51a6600567b2e1ed76346853be6613` |

### `results/pilot/tally-witness/results/gemma__*.json` (43 files, Gemma-4-31B-IT, page + 3 tiles (spike v1))

Source: `../spikes/tally-witness/results/gemma__*.json`, same file names.

| File | sha256 |
|---|---|
| `gemma__010441C0100.json` | `fd0a597992c438aa7070a818e312a07834b8e079e15489f6e7a837c2998ede50` |
| `gemma__010445C0100.json` | `f5bf98ffd74e930817efe8b630c057fc7c9636314f2ca6e1ae6c117c41aab4bb` |
| `gemma__010452B0100.json` | `91654d74b1fc2296b914274ab25613d8aa6fc892f16013d31a09696a94d4a8b8` |
| `gemma__010474B0100.json` | `a7dc4b6f0ade97997aa7b0bb146865e1aec35421fbf4f9f0dc893cad05dbcdd1` |
| `gemma__070159C0300.json` | `76e1094a4c8d8e87b77f5e10ab68ef5793e43c307251ebfd9c0507bf78abd1c3` |
| `gemma__070332E0100.json` | `5cc528d735c830e1fc12aa00524c52315d0eab214cc8aa1a5848f79708e0cfb7` |
| `gemma__070394C0100.json` | `6941ae02e0f3ec98f6c3ae9614a034d80b83c30d48785746b0242af95064e84b` |
| `gemma__072055C0300.json` | `319d0309815b8d799e05c0ebfa4643395a63ef5b50da5bb8f60fc9d1a85cd295` |
| `gemma__093954C0200.json` | `65c0c1ca3b1fbbd666d74343ff08a08e71b56ec6dce517d50a4dd0b1b29984d0` |
| `gemma__095566C0300.json` | `86f2f54ee5b72689024114c3ca87f8a9b4fbb78006c740dd20446e29f67e18fc` |
| `gemma__120293C0100.json` | `f3c377966c8e7b491d7a8b797d3bd25e65242599bfaa223f41ba6c0c82d2a660` |
| `gemma__120295C0300.json` | `5f3ae60a373190ff38cdc297643c96307d52e833a813314ce0fefa901e708dfd` |
| `gemma__120301C0400.json` | `1a620aa56893e6827587c2c5436618ce8ea7b2a704e158f19f82f986ce49d4a9` |
| `gemma__120306C0900.json` | `a4d5bc70a13c439ba5e0dc8da9d62bc7f522039828849b751908d614422e9ef2` |
| `gemma__122837B0100.json` | `1e968789d6e143d5683d5f98aff9024e8fde48a61794715d1ed22df152ef5b54` |
| `gemma__122838C0100.json` | `c36be508005fbcd1858ad7fe2196887e0c49dc4a5e3bc98408a00e6770c2b093` |
| `gemma__141097C0100.json` | `e6691d5ed33bdf273cc65e4b8ff0e1f59997bdd8e6d19eef51ba2d7e0bd8842a` |
| `gemma__151794C0200.json` | `c310ebf7fe245e08d4f43ed478fa3e11ca980511c1c9cbfa23043a2ebfc8ddb1` |
| `gemma__151806B0100.json` | `a0d5c761dcb1fca9858fe628b53e96dc7b2a6069939c880abdb07da298e6fc97` |
| `gemma__156034C0100.json` | `01e6847ad55b629078604ccd7486466f98dea7acac96427af2c7633f17082dba` |
| `gemma__156044B0100.json` | `d3a339130a2fdc6b2f1a3500b0470e25ad74fdc75e1ccfd680dae42aa5574ad3` |
| `gemma__156723B0100.json` | `1da9664dcda49817aae873dcfff66038060ab79c26c745ad246ea19a1e72f6dd` |
| `gemma__191790C0100.json` | `3c8d9b7111ac4ff8a22fcbd608870df57e8990e0fca0569959572321b8b332ab` |
| `gemma__200144B0100.json` | `bdfa9f21dfb4eb235c868c4119f8576ef2dffef528aedfc9f95600eba3dcc90e` |
| `gemma__200742B0100.json` | `3119e141ebcf8f5d1ac9cf47fb952a3a45075d8457c13178a7e51828e15ea9e5` |
| `gemma__201280B0100.json` | `4df2008b0fc2c670a4452644923cb673c7fec4efe962b05aabd8242e31dc3a2b` |
| `gemma__201717C0100.json` | `7cd1ee579b5d3307efb909950fac9ec3034bcc41621052fdc9890f2c679544f6` |
| `gemma__201720E0100.json` | `458b79fdc16307d44b474db81560742d58dda6f7a08cbb58d28da43c7ea728ea` |
| `gemma__201791B0100.json` | `98d6a1a01d32e54a137f2a4f2e04a6b81806d2ad6603611215f2728f65cd74b7` |
| `gemma__202156B0100.json` | `721d14d053aab6c5a3895999fbc212e549540f61385f78c87ce5f344c6b6f3bb` |
| `gemma__202338B0100.json` | `39e41c854550b1b3692e54f1b3c18b54fe178706cc15e133630defa7a2bed935` |
| `gemma__202451B0100.json` | `511f7700ca677559f8fe5b7ee61a5c56ca8940929f3d586fb47359ddfad175d7` |
| `gemma__211294C0100.json` | `176af75d83b17e3fcbe51fd76313b855eb45e549d51711197688a9fe780b3710` |
| `gemma__211298B0100.json` | `e372f1eb66fa8999891362938d6860a338198118b309ca45912a5ee74eb4efd2` |
| `gemma__211420C0400.json` | `784da16cbfbd24d40955a59add40919595b3154af694aee1b9130d9f7c32c192` |
| `gemma__300449C0100.json` | `0129fc10e4989ae064ffa3e3be0b9c4e364f96074c8fff0a26a2a4cd151bf2be` |
| `gemma__302296C0200.json` | `7e8793e474cf099bc4bc52ad4fa2a70fbf7d6fd1455d85675cba9660def25bb3` |
| `gemma__302307C0100.json` | `b4fe0ed3136da983a31ceb4976c3eedcb891ab7ddd8d12d62431244de5031a83` |
| `gemma__302539C0100.json` | `c616e4df2ec11219a02b9e0a816d569af15fdd526e59903ad4935f657ea06fea` |
| `gemma__302541B0100.json` | `490ec17cdb70b940d2ad9b3cf63dfe2fcb6eb4eb954ff3b2144de97955bbfb47` |
| `gemma__304052B0100.json` | `ea81acaf0955048f2f0ed496be8c1b7a40a8ab3db1e7f1c8ab1830f7b7eb41db` |
| `gemma__304069B0100.json` | `1a047ee4bafeda47cb3b8536e775d18d151308d0ed1dcf570e5e02ae00e2a891` |
| `gemma__304968C0100.json` | `2a8a80a797a8c6d623c2b35c054b53952b8cfa08d02e66e6318733d67e325537` |

### `results/pilot/tally-witness/results/qwen__*.json` (43 files, Qwen3.8-27B, page + 3 tiles)

Source: `../spikes/tally-witness/results/qwen__*.json`, same file names.

| File | sha256 |
|---|---|
| `qwen__010441C0100.json` | `548556383e939441d1fc669989a909b9426d6a7183d5c9a8c380af96518cdc79` |
| `qwen__010445C0100.json` | `fe4e94fa08923349ca58ae21da3d01c083e46d0e3b094a9c45e871158ad735de` |
| `qwen__010452B0100.json` | `b7377550cf63b231e56a603cc63e5f9b0cbfb910845f11731fb9849dbc7c5a66` |
| `qwen__010474B0100.json` | `6b16202f0fa005701ec865a98cdd7e73e5fc6cfe40d1acd06c2177bcc97096fb` |
| `qwen__070159C0300.json` | `fc40653a42cbaae653143ca2e103f2ab88ebc491255aa06d080ef83ada252f11` |
| `qwen__070332E0100.json` | `fe2d53ac919d32bb02687b69fb1ebf84c552e7e3279f2ae8c2df678adccf4655` |
| `qwen__070394C0100.json` | `717ba2a55f3ba4e71d6cc7862e76e0e925f6929e7e02dc9b0868668c688837a6` |
| `qwen__072055C0300.json` | `05b8834c010ea6cf753420c9171899acda8da20fb13158bcbd52503ce19c786f` |
| `qwen__093954C0200.json` | `0d0fe0d92941dc58fafc2e3e353ff1c62219395be91723aeda129c0a2dafba65` |
| `qwen__095566C0300.json` | `ebda5b5a4e501625b0d5edfe289884754d359477ed62d8df1e0e595a98e21e04` |
| `qwen__120293C0100.json` | `5f6823bca4251f76dfc42bdc3c04bde8ca0e6366d1972eddba80c227ac0848e2` |
| `qwen__120295C0300.json` | `c3adcc0aad23696ee82e4342dc4a8f8dd18d94d1799341b131032ed37206da8a` |
| `qwen__120301C0400.json` | `9c3e5b2e1fcea4e5100859deca244d32ed4bacaf143841f275b1ac7dc0b4cafd` |
| `qwen__120306C0900.json` | `0b664393aa32553aa9c3efd976bc151d33c50ad9fbb00bf1515605b444f4bbb1` |
| `qwen__122837B0100.json` | `b5bb574e76feea241467a1a5dc653382fc0c3fd0efd938bac73c9b58ece30886` |
| `qwen__122838C0100.json` | `22726d53023981cc6be2cfee6bab3a5e83230368877738054ba51c2c9a882ab0` |
| `qwen__141097C0100.json` | `f1b0043cfebeb538ef9887593d3516beb21097af6af1c37883fc44cc6270e9e2` |
| `qwen__151794C0200.json` | `3ce4448132e4fec5bfeb277f1faadbb09dc8e41e9148c9d54afe04fae5f16b56` |
| `qwen__151806B0100.json` | `0a3acf63482b60134aa3ec048be83c8659753d5d6c5a8b6cbd233d27447f34c0` |
| `qwen__156034C0100.json` | `02012fda3b62c948927ca62e19850bc638e3bda2d008d58e68a3a81b3b126814` |
| `qwen__156044B0100.json` | `61732aaceab280b2b2a6ef270a43adb6f260785e25270b92ccd6fad68340335e` |
| `qwen__156723B0100.json` | `797492c6cdfc4ff7f24b46d2c2117319b93a593915ffa37bcd938dd172bf3dc0` |
| `qwen__191790C0100.json` | `3cdff980bbc95429451f56e6c9bbc4b0cd7ecb8b4a1d37dab861991338ab3770` |
| `qwen__200144B0100.json` | `59c63e46812a21f9cbb4c0843aad96111c4528a5deda1d10f42957c17ffbde17` |
| `qwen__200742B0100.json` | `ff71d318fd32b0d2db7079922dfe770d819e736f6c52df9d57cbad1900718bd9` |
| `qwen__201280B0100.json` | `7cd32d67216b1e4a02fc7457d747daa97dd5a1c1d0dce9319fa0fb04cc31c767` |
| `qwen__201717C0100.json` | `8a4f966ce6d3599ad58cf225633edf640eee88feddd467e1a8b8fe75190874cd` |
| `qwen__201720E0100.json` | `10d256df9440b9dd13f4da459a7fcd638a082fa49e74c7bd6ee0f83e5eae7e75` |
| `qwen__201791B0100.json` | `e6b111762fd237009d00aaa0ed7173b96d078d896e4be8e5e2642f4824100676` |
| `qwen__202156B0100.json` | `bce9e33e07ef0be7b0c2c5ed1c7df349e395e7dde802b8976c9b797fcde7fe0c` |
| `qwen__202338B0100.json` | `9144b559f049ee6c1897ccd7431ba879bc5012c7ad3497553bf53830a2e9bf09` |
| `qwen__202451B0100.json` | `438bd42373c930042257308ab2e4283d2b1117b0159b966f4e2645d6f5dd9c2a` |
| `qwen__211294C0100.json` | `6232390dce970f7bc12b364cc62520a833ff564a8939b1143c7b03cf5f4fcd88` |
| `qwen__211298B0100.json` | `da410976abc8462847c31862465a9d22fd3ffb7648f726987881dac83b060edc` |
| `qwen__211420C0400.json` | `41eed10e3e8f08f00d4778163e3fe633741e9143a3281e57090a0ad8bd778f65` |
| `qwen__300449C0100.json` | `5ba13e046969fb3094141927554b419fd6228fdb5f443c6d395e750b73202768` |
| `qwen__302296C0200.json` | `ca31710cf055cb42fe8964f8462eae37d7af23455c63ea3f610c65a1406734e7` |
| `qwen__302307C0100.json` | `ca513ec59fc3f0b82c5c920e44eeb5efcb8d3c22c575178a42d4c9cde2df9c40` |
| `qwen__302539C0100.json` | `a1850dcf1eafc030a511d434f2c7c4d43aff925684a6e09d9d3139ab8fb83d09` |
| `qwen__302541B0100.json` | `4ca1417826949e777bca2dec590240b215838405ecf14a9dbf8fa484868759cb` |
| `qwen__304052B0100.json` | `f853e0f10bc262cd34fa467f5e1335824c68fb26bf8822cf890346325a3d84f4` |
| `qwen__304069B0100.json` | `f8a0c1416e327fc40608c0270376724d52e1f12c0c6db888a33762a3bb040d99` |
| `qwen__304968C0100.json` | `fef12eb9d929727b0f0f75a3a040d32429813a8a0957b7e65f907061d714b676` |

### `results/pilot/ledger-rescue/gemmatile__*.json` (40 files, Gemma-4-31B-IT, whole sheet + 3 strips)

Source: `../spikes/ledger-rescue/results/gemmatile__*.json`, same file names.

| File | sha256 |
|---|---|
| `gemmatile__ARDNAMURCHAN-LIGHTHOUSE__01.json` | `7bc00e700d03888b8a3087bf6f1d9ef053f52ca41e59ac2666b0f2634195ff54` |
| `gemmatile__ARDNAMURCHAN-LIGHTHOUSE__02.json` | `6e3353ac4f06b3cfa994aa40a719e34cdeee69966b74d892655d308fe99a9e34` |
| `gemmatile__ARDNAMURCHAN-LIGHTHOUSE__03.json` | `d9075682164a84598dbac40acb8a65c4ea72ea59eceb49784ceff3847b4d1c9b` |
| `gemmatile__ARDNAMURCHAN-LIGHTHOUSE__04.json` | `997c394714dddea2e383303d09bd438bb19a06cac1c5a73d49b57a0a5001b6b5` |
| `gemmatile__ARDNAMURCHAN-LIGHTHOUSE__05.json` | `458f838061e62e925fd421eb0e00ff3c9df03564dc8042fdd2fa232f8c4da185` |
| `gemmatile__ARDNAMURCHAN-LIGHTHOUSE__06.json` | `fbcb209c8a90629ccfe40a30b27b389582e1e92c52f685be5c9a9a11f92f6681` |
| `gemmatile__ARDNAMURCHAN-LIGHTHOUSE__07.json` | `880b7d57c71b480361696211b1435c9ccb934500fecc733c550da06a1acbba32` |
| `gemmatile__ARDNAMURCHAN-LIGHTHOUSE__08.json` | `f71e490cd007f8630003ddc04791a772748742ddf24fda1bc4fb4aadf15c8c76` |
| `gemmatile__ARDNAMURCHAN-LIGHTHOUSE__11.json` | `cde1131e4365f33d9c4522c834bdb08a5e788cf1dd26f9c86546182aae8c86cd` |
| `gemmatile__BALCOMBE-GABLES__00.json` | `2c19d7a59671df951edf652b97e1935363ac0047805a05587f7857bea53a449b` |
| `gemmatile__BALCOMBE-GABLES__01.json` | `b6b4ca92df330aaadbb05b0ff337ce7a02e4917bce1a2e1f4159bb84ee02c435` |
| `gemmatile__BALCOMBE-GABLES__02.json` | `28e024aac1789bc1e0b992cd4847e27429f538f86d82e4944b2a632b28236939` |
| `gemmatile__BALCOMBE-GABLES__03.json` | `7bdd4ae2e964cc51dd3538152f87207d937c36f70d33ee68c5ab831db9ffae1f` |
| `gemmatile__BALCOMBE-GABLES__04.json` | `4efc1fa8f2f1e491a944aa0b06ae4eff109330fa96f4297bb1e92889dc90461a` |
| `gemmatile__BALCOMBE-GABLES__05.json` | `6d6273227ca675c4549fb5e29d652ad28743d355fba1995d1f13a6f35f95daf0` |
| `gemmatile__BALCOMBE-GABLES__06.json` | `4337b060e31763d8c87385e9939f4604ecef55706abac3d184f252054d5143b7` |
| `gemmatile__BALCOMBE-GABLES__07.json` | `3c82e2f9c1841776cdd196b34b62a5305f02f870e161999f1154b75e7c6fc276` |
| `gemmatile__BALCOMBE-HIGHLEY-MANOR__01.json` | `e145abe12ee7cf782517cbd655c7131cd173470edf6ad3ac6d86b578b09c13f4` |
| `gemmatile__BALCOMBE-HIGHLEY-MANOR__02.json` | `991498f61cfe3fef0e77f9064a4267d8bab94dafd724f3a9afdbd702810fd3c3` |
| `gemmatile__BALCOMBE-HIGHLEY-MANOR__03.json` | `0f61512108e37e6174cd40b3efd66c69ea069738fff1e8dc14842f6a8cfcd066` |
| `gemmatile__BALCOMBE-HIGHLEY-MANOR__04.json` | `bb3d7789dcd45b278f494f7909bd787a056c7006d303b6e2a4841ad7931de020` |
| `gemmatile__BALCOMBE-HIGHLEY-MANOR__05.json` | `991bbd68fc7c7da4e9dcbf265204f6a2c69fea8b42e528ad63f657d37ec1f1aa` |
| `gemmatile__BALCOMBE-HIGHLEY-MANOR__06.json` | `70f53aa599850ff979123e33e5364ed8ec4fa4eca45588e685a70b7afd0cbf2e` |
| `gemmatile__BALCOMBE-HIGHLEY-MANOR__07.json` | `8c17116c4f0f8d42b22ccb29d91e71c55442e77113d1e22680f989bbfe45a8c0` |
| `gemmatile__BARKBY-HALL__00.json` | `d7312a914a657fc21eb69614409d844eeef62b2bfb166cb089b08cf2d5f970c8` |
| `gemmatile__BARKBY-HALL__01.json` | `3c594e9cf976b621ce8c9a1db353ef4b0c9d12cba16d37d8725a8024ad9f7a40` |
| `gemmatile__BARKBY-HALL__02.json` | `89a8b7cb943f56e2623e664d4f4b2a5585fe5d8ddb8ebf7cbd91fb66db0d57c4` |
| `gemmatile__BARKBY-HALL__03.json` | `f18d46e113bcf1ff5185667d44cc80b168ba8770659ee9a4578f8f8012b72bd5` |
| `gemmatile__BARKBY-HALL__04.json` | `38fc8d8c1b5774d03dec576937d0cfa7a30d9281977d9924f04d1f20dabbded3` |
| `gemmatile__BARKBY-HALL__05.json` | `d8285f876c60fd2f0f9728e5654bc2c87a7feb343634cb80189b9f33354b2c74` |
| `gemmatile__BARKBY-HALL__06.json` | `885d59ed14d30ed9473c81d3003409ab07d959554303feca6f187f7392f1339c` |
| `gemmatile__BARKBY-HALL__07.json` | `77aa29aac2e079780ff52047fabb2d6cbef425d1c1d3953ca48ec6a01be5e00f` |
| `gemmatile__BARKBY-HALL__08.json` | `4c2c3410113e00be0e8b8f9ef5999193124fbaace5432b0c41e5a7cc67d981f2` |
| `gemmatile__BARROWFORD-RES__01.json` | `4fd0a5f594fd4e69dea0c49dc50c9e410606d498cc326ca28be5bef577266deb` |
| `gemmatile__BARROWFORD-RES__02.json` | `61d034633f79e427602e0e740189807e6faecb900dc63e61b323d901d3946414` |
| `gemmatile__BARROWFORD-RES__03.json` | `73f749f36c4fb762f9e485205b8585bf15a6ff5e37e779da4a16cc2e0ab1ab39` |
| `gemmatile__BARROWFORD-RES__04.json` | `3702c754a9ca20040127961be09a74c86038d9495c508e7842a57a076c8ea379` |
| `gemmatile__BARROWFORD-RES__05.json` | `747ceab31d3527a07384b4e5688f75bd6d50ed357717431a7bdf1f1feb92df37` |
| `gemmatile__BARROWFORD-RES__06.json` | `c5635ef2a22c3f39bf3575b7da44ee072a2ff19b0603b6964c55adbace683311` |
| `gemmatile__BARROWFORD-RES__07.json` | `a789f1c172d915834892e822680564b68aad94e1389cba00fa3c1b50974bee89` |

