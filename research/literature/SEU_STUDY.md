# Single-Event Upsets as a stress-test domain

**Status of this document:** a literature study. Nothing in this repository
has observed a physical upset. All experiments are SIMULATED (see EXP-G). The
physical claims below are LITERATURE_SUPPORTED at best, and each cites its
evidence id.

## 1. Definitions (not synonyms)

| Term | Meaning | Source |
|---|---|---|
| radiation event | a particle (alpha from packaging, neutron-induced secondary, heavy ion in space) traverses the device | LIT-016 |
| physical interaction | ionisation → charge deposition along the track | LIT-016 |
| electrical disturbance | collected charge at a sensitive node produces a current transient | LIT-016 |
| state upset (SEU) | the transient exceeds the critical charge of a storage/latching element, which flips state; non-destructive ("soft") | LIT-001 |
| multiple-bit upset (MBU/MCU) | one event upsets several cells | LIT-001 |
| single-event transient (SET) | a transient in combinational logic; it matters only if latched | LIT-001 (soft-error family) |
| error | the part of system state that may lead to failure | LIT-002 |
| detected error / corrected error | an error caught by a mechanism (parity, ECC) and possibly repaired | LIT-007, LIT-011 |
| SDC / DUE | silent data corruption / detected unrecoverable error | LIT-011 |
| failure | deviation of delivered service | LIT-002 |

The informal intuition "something changed one bit without an intended software
instruction" collapses at least four of these rows into one. It also includes
things that are not SEUs at all: marginal timing, voltage droop, Rowhammer-type
disturbance, firmware bugs, and hardware wear-out (hard errors).

## 2. Physical → computational chain

For each arrow: can it be observed, how, at what resolution, and what is lost?

| Transition | Observable? | Typical evidence | Information lost |
|---|---|---|---|
| particle → charge deposition | only in beam or detector experiments | beam tests (JESD89-style), particle counters | which particle, where, when |
| charge → node disturbance | device simulation (TCAD) or test structures | circuit-level simulation | the analogue waveform |
| disturbance → bit flip | yes, if the cell is read or scrubbed | ECC logs, parity errors, scrub reports | exact time of flip (only a bound between writes/reads/scrubs) |
| bit flip → architectural state | if the bit is architectural and read | machine-check events, register/memory dumps | microarchitectural path |
| architectural → execution trace | with tracing/instrumentation | trace diffs vs a golden run | whether the flip was ACE |
| trace → program behaviour → observable consequence | yes, at the output | wrong output, crash, hang | usually everything upstream |

**Critical distinction:** detection establishes **inconsistency** (a parity or
syndrome violation). It does not establish **cause**. An ECC syndrome infers a
location *under an assumed fault model*. EXP-G shows, in simulation, that the
inferred location is right for all single flips and wrong for all double flips
under Hamming(7,4) (H-011 DERIVED, DRV-005).

## 3. Detection and mitigation mechanisms (literature)

Parity (detects odd-weight errors). Hamming SEC and SECDED ECC (LIT-007).
Chipkill and symbol-based codes. Memory scrubbing, which bounds how long a
latent error can accumulate into an MBU. Lockstep and redundant execution
(DMR/TMR voting). Watchdogs. Machine-check architectures that log corrected
and uncorrected errors. Radiation-hardened cells (DICE latches). Error-rate
derating by vulnerability factors (AVF, LIT-011). *Verification status:* this
is a standard engineering summary from agent knowledge (LIT-016 and LIT-011 are
not yet verified, Q-011).

## 4. Case studies

Each case lists what is actually demonstrated.

### CASE-001: Qantas Flight 72 (A330-303 VH-QPA, 7 Oct 2008)
- **Known observations:** intermittent spikes in ADIRU output data (AOA among
  them). The flight control computers commanded two pitch-down manoeuvres, and
  there were injuries.
- **Official explanation (LIT-005):** a combination of an FCPC
  AOA-processing design limitation (it could not handle multiple spikes 1.2 s
  apart) and an ADIRU failure mode in which the CPU module combined one
  parameter's data with another parameter's label. The failure mode was
  *probably initiated by a single rare type of internal or external trigger
  event* combined with marginal hardware susceptibility. There are 3 known
  occurrences in >128 million unit-hours.
- **Alternative explanations considered:** single-event effects were
  considered and **not ruled out, but not established**. Other trigger types
  were also not excluded.
- **What is demonstrated:** a data-corruption failure mode and a
  software design limitation. The physical trigger is **UNRESOLVED**.
  Describing QF72 as "caused by a cosmic ray" overstates the evidence.

### CASE-002: Schaerbeek, Belgium e-voting (18 May 2003)
- **Known observations:** one candidate's electronic tally exceeded the
  manual recount by exactly 4096 = 2^12 (LIT-006, secondary sources only).
- **Proposed explanation:** a single bit flip at bit position 12, possibly
  from a cosmic-ray SEU.
- **What is demonstrated:** the arithmetic signature (the discrepancy is a
  power of two) makes "one bit of the stored count changed" a strong
  **INFERRED** explanation of the *state change*. The *physical mechanism*
  (particle strike vs. another cause) is **not demonstrated**. The official
  report has not been consulted here.
- **Lesson for this repository:** a difference in the output representation
  can support inferences about the *kind* of state change (a projection that
  preserves bit-position information). It cannot support inferences about the
  *physical cause* (the projection's kernel contains all causes that produce
  the same flip).

## 5. What this repository can and cannot do

- **Can:** simulate injected state changes in models (clearly labelled), and
  measure masking, detection, miscorrection and propagation across simulated
  layers.
- **Cannot (hardware boundary, OP-005, Q-009):** observe radiation events,
  charge deposition or real upsets. Required instrumentation: dedicated test
  hardware with ECC error logging, and beam or high-altitude exposure under an
  authorised test plan. Until then, every physical statement is at most
  LITERATURE_SUPPORTED.
