# MIL-STD-1553B Dual-Redundant Serial Bus Interface Specification
## EdgeSAR Radar Sensor Remote Terminal (RT) Integration

**Document ID:** EDGESAR-BUS-1553B  
**Version:** 1.0.0  
**Standard:** MIL-STD-1553B Notice 2 (Aircraft Internal Time Division Command/Response Multiplex Data Bus)  
**RT Address:** `0x05` (Binary: `00101_b`)  
**Baud Rate:** 1.0 Mbps | **Modulation:** Manchester II Bi-Phase Level  

---

## 1. Word Formats & 20-Bit Physical Layer Encoding

All transmissions over the dual-redundant bus channels (Bus A and Bus B) consist of 20-bit words with a nominal $1.0\ \mu\text{s}$ bit period ($20\ \mu\text{s}$ total word duration):
- **Sync Field (3 bit times)**: Unbipolar invalid Manchester waveform for word synchronization.
- **Payload Field (16 bit times)**: Data / Command / Status bits (MSB first).
- **Parity Bit (1 bit time)**: Odd parity across the 16 payload bits.

```
 0                   1                   2                   3
 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
|Sync |        16-bit Payload           |P|
+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
```

### 1.1 Command Word Format (BC -> RT)
Transmitted by Bus Controller (BC) to initiate transfers:
- **Sync**: Command/Status Sync ($1.5\ \mu\text{s}$ High, $1.5\ \mu\text{s}$ Low).
- **RT Address (Bits 1–5)**: `00101` (EdgeSAR RT Address 5).
- **T/R Bit (Bit 6)**: `0` = Receive (BC writes to EdgeSAR), `1` = Transmit (EdgeSAR reports to BC).
- **Subaddress / Mode (Bits 7–11)**: `00001` to `00100` (Subaddresses 1 to 4).
- **Data Word Count / Mode Code (Bits 12–16)**: `00001` to `11111` ($1$ to $31$ words; `00000` = $32$ words).
- **Parity (Bit 17)**: Odd parity.

### 1.2 Status Word Format (RT -> BC)
EdgeSAR response indicating operational state:
- **Sync**: Command/Status Sync.
- **RT Address (Bits 1–5)**: `00101`.
- **Message Error (Bit 6)**: Set if invalid parity, Manchester violation, or illegal word count.
- **Instrumentation (Bit 7)**: Logic `0`.
- **Service Request (Bit 8)**: Set when new high-confidence ATR detection ready.
- **Reserved (Bits 9–11)**: Logic `000`.
- **Broadcast Received (Bit 12)**: Logic `0`.
- **Busy (Bit 13)**: Set if embedded DSP DMA processing buffer full.
- **Subsystem Flag (Bit 14)**: Set on hardware BIT fault (temperature, power rail).
- **Dynamic Bus Control (Bit 15)**: Logic `0`.
- **Terminal Flag (Bit 16)**: Logic `0`.
- **Parity (Bit 17)**: Odd parity.

### 1.3 Data Word Format
- **Sync**: Data Sync ($1.5\ \mu\text{s}$ Low, $1.5\ \mu\text{s}$ High).
- **Payload (Bits 1–16)**: 16-bit two's complement integer, unsigned integer, or bitfield.
- **Parity (Bit 17)**: Odd parity.

---

## 2. Subaddress Memory Map

| Subaddress | T/R | Direction | Message Name | Words | Update Rate | Description |
|---|---|---|---|---|---|---|
| **SA 1** | R (`0`) | BC -> EdgeSAR | Radar Configuration | 8 words | 10 Hz (Asynch) | Operational mode, chirp bandwidth, CFAR $\alpha$, noise cutoff |
| **SA 2** | T (`1`) | EdgeSAR -> BC | Health & BIT Status | 4 words | 50 Hz (Periodic) | Peripheral state, DMA overruns, temperature, supply rails |
| **SA 3** | T (`1`) | EdgeSAR -> BC | CFAR Target Detections | 16 words | 25 Hz (Periodic) | Detected range bins, interpolated peak offsets, local SNR (dB) |
| **SA 4** | T (`1`) | EdgeSAR -> BC | ATR Target Classification | 12 words | 10 Hz (Periodic) | Vehicle class (T-72/BMP-2/BTR-70), confidence, coordinates |

### 2.1 Subaddress 1: Radar Configuration (BC -> EdgeSAR)
- **Word 1**: Operating Mode (`0x0001` = STANDBY, `0x0002` = RAW_STREAM, `0x0003` = AUTONOMOUS_ATR).
- **Word 2**: PRF Selection (`1000` Hz default).
- **Word 3**: Chirp Bandwidth Index (`0x0001` = 100 MHz, `0x0002` = 150 MHz).
- **Word 4**: CFAR Training Cells $N_T$ (Unsigned integer, default: `8`).
- **Word 5**: CFAR Guard Cells $N_G$ (Unsigned integer, default: `2`).
- **Word 6**: CFAR Threshold Multiplier $\alpha$ (Q8.8 fixed point, default `3.5` = `0x0380`).
- **Word 7**: Noise Floor Cutoff $T_{\text{floor}}$ (Q8.8 fixed point).
- **Word 8**: Checksum (16-bit XOR sum).

### 2.2 Subaddress 4: ATR Target Classification Report (EdgeSAR -> BC)
- **Word 1**: Frame Sequence Counter (Monotonically increasing).
- **Word 2**: Detected Target Count ($0$ to $3$).
- **Word 3–5 (Target 1)**:
  - Word 3: Class ID (`0x0001` = T-72, `0x0002` = BMP-2, `0x0003` = BTR-70).
  - Word 4: Softmax Confidence (Percentage scaled $0 \dots 10000 \implies 0.00\% \dots 100.00\%$).
  - Word 5: Slant Range Coordinate (meters, unsigned 16-bit).
- **Word 6–8 (Target 2)**: Class ID, Confidence, Slant Range.
- **Word 9–11 (Target 3)**: Class ID, Confidence, Slant Range.
- **Word 12**: Status & Explainability Flag (`Bit 0`: Grad-CAM verified, `Bit 1`: Shadow verified).

---

## 3. Bus Scheduling & Dual-Redundant Failover Policy

### 3.1 Major & Minor Frame Architecture
- **Major Frame Cycle**: $100\text{ ms}$ ($10\text{ Hz}$ overall system update cycle).
- **Minor Frames**: $5 \times 20\text{ ms}$ frames ($50\text{ Hz}$ bus clock).
  - *Minor Frame 0*: SA2 (Health/BIT, $50\text{ Hz}$) + SA1 (Config, if commanded).
  - *Minor Frame 1*: SA2 + SA3 (CFAR Targets, $25\text{ Hz}$).
  - *Minor Frame 2*: SA2.
  - *Minor Frame 3*: SA2 + SA3 (CFAR Targets) + SA4 (ATR Report, $10\text{ Hz}$).
  - *Minor Frame 4*: SA2 + Spare Bus Bandwidth.

### 3.2 Dual-Redundancy & Failover State Machine
1. **Primary Channel**: Transmissions default to **Bus A**.
2. **Channel Monitoring**: If the Bus Controller experiences no response within the response time-out interval ($14.0\ \mu\text{s}$), or detects a Manchester encoding violation or bad parity:
   - BC retries on Bus A once.
   - If retry fails, BC automatically switches communication to **Bus B**.
   - Increments bus channel error counter and sets BIT warning flag in Subaddress 2.
3. **No Interruption**: EdgeSAR dual-channel transceivers maintain galvanic transformer isolation, ensuring that a short or open circuit on Bus A does not degrade Bus B transmission.
