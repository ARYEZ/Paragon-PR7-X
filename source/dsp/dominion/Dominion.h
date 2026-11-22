#pragma once

#include "dsp/eq/EqDesign.h"
#include "dsp/effects/EffectUtils.h"

#include <array>
#include <atomic>
#include <vector>

// DOMINION (stomp 5, PR7-E 0.10.0): a dynamic resonance suppressor,
// inspired by oeksound soothe 3 as its manual describes it (it finds the
// resonant peaks in the sound as it plays and turns them down with filters
// that follow them). soothe's algorithm isn't published: this is our own
// design, and its numbers are our choices.
//
//   - A bank of filters 1/12 octave apart, 20 Hz to 20 kHz, each listening
//     to its part of the spectrum (a 1/6-octave band pass) and measuring its
//     level.
//   - SOFT: a part is a resonance when it sticks out above the parts around
//     it (their average over up to an octave either side, less for higher
//     DETAIL), whatever the overall level. HARD: when it's over a fixed level
//     (lower for more DEPTH), so it depends on how loud the track is.
//   - DEPTH scales how much of that it takes away, the depth curve (bands
//     you draw, like an EQ) scales it across the spectrum, MAX CUT limits it.
//   - The cuts: a bell for each filter, as narrow as DETAIL says (half an
//     octave to a sixteenth), gains solved so the bells together make the
//     cut wanted (they overlap), moving with ATTACK and RELEASE (faster for
//     higher frequencies, and shaped by the tilts).
//   - Zero latency: no look-ahead (like soothe's low-latency mode).
//   - Stereo: left/right or mid/side, LINK (listen to both together or
//     each alone) and FOCUS (more on one, less on the other).
//   - Then WET TRIM, MIX, DELTA (only what it takes away) and OUT.
namespace dominion
{
    // Saved by index: only ever add to the end.
    enum class Mode { soft, hard };
    inline const juce::StringArray modeNames { "Soft", "Hard" };
    enum class StereoMode { leftRight, midSide };
    inline const juce::StringArray stereoNames { "L/R", "M/S" };
    enum class Shape { lowCut, lowShelf, highShelf, highCut, bell, bandPass, bandReject, tilt };
    inline const juce::StringArray shapeNames { "Low Cut", "Low Shelf", "High Shelf", "High Cut", "Bell",
                                                "Band Pass", "Band Reject", "Tilt" };

    // The ENGINE (0.25.0): CLASSIC is DOMINION as it was (0.10.0); REFINED is
    // fitted to measurements of soothe 3 (renders of our test signal through
    // it at 28 settings, tools/soothe-match): its knobs read as soothe's do
    // (DEPTH 0 to 10 as soothe's, beyond it further; DETAIL, ATTACK and
    // RELEASE 0 to 100 % as soothe's 0 to 10), its own sense of where to work
    // (much less in the lows), its timing, and a LOOK-AHEAD. Saved by index:
    // only ever add to the end.
    enum class Engine { classic, refined };
    inline const juce::StringArray engineNames { "Classic", "Refined" };

    // REFINED's numbers, the ones fitted to the measurements. A struct (not
    // constants) so the fitting harness (tests, "[domfit]") can try others.
    struct Tuning
    {
        // DEPTH: the cut grows as ((depth - depthStart) / (5 - depthStart))^depthPower, x depthScale at 5.
        double depthStart = 2.24, depthPower = 1.29, depthScale = 0.631;
        // SOFT: a part has to stick out by margin dB (DETAIL 0 to 100) before it's cut.
        double margin0 = -0.143, margin100 = 4.03, knee = 1.17;
        // DEPTH lowers that margin (dB per step above 5, raises it below), and DETAIL scales the cut (x at 0 and 100, 1 at 50).
        double marginDepth = 0.913, detailScale0 = 0.297, detailScale100 = 7.18;
        // How the cut grows with how far a part sticks out (dB over the margin, to this power: under 1, big peaks less, small ones more).
        double overPower = 0.581;
        // How wide a cut is (octaves to half its depth) and how far round a part SOFT looks (octaves either side).
        double width0 = 1.76, width50 = 0.539, width100 = 0.105;
        double window0 = 1.0, window100 = 0.33;
        // SOFT's sense of where to work (fitted: soothe hardly cuts below 500 Hz): a weight on the cut at 25 Hz, 50 Hz ... 12.8 kHz (an octave apart), in between on a log scale.
        std::array<double, 10> weight { 0.0, 0.0, 0.0, 0.11, 0.0467, 0.3, 0.6, 1.0, 0.8, 0.5 };
        // Timing at 1 kHz: ATTACK at 0, 25, 50 and 100 %, RELEASE at 0, 50 and 100 % (ms), and how they scale with frequency.
        double attack0 = 30.7, attack25 = 46.2, attack50 = 107.0, attack100 = 280.0;
        double release0 = 37.0, release50 = 96.7, release100 = 797.0;
        double timingPower = 0.5;
        // HARD's attack and release against SOFT's (soothe's HARD grabs slower and lets go sooner).
        double hardAttack = 2.71, hardRelease = 0.396;
        // DETAIL slows the attack and quickens the release: factors at DETAIL 0 and 100 (1 at 50).
        double detailAttack0 = 0.477, detailAttack100 = 4.2, detailRelease0 = 1.35, detailRelease100 = 0.65;
        // HARD: the level (dB per part, tilted up hardTilt dB an octave) where it starts at DEPTH 5, how much lower per step, its slope.
        double hard5 = -22.8, hardStep = 5.02, hardSlope = 0.325, hardTilt = 6.14;
        // ... how much faster that falls the further DEPTH is from 5 (dB per step squared), and how evenly HARD works
        // across the spectrum (0: where SOFT does, 1: everywhere alike).
        double hardCurve = 0.463, hardFlat = 1.0, hardKnee = 36.3;   // ... and how gently it starts (dB)
        // Listening: each part's level is smoothed over this many cycles (4 ms to 120 ms).
        double cycles = 16.0;
        // LOOK-AHEAD: how far ahead (ms) the cut sees; the rest of the delay is just delay.
        double leadMs = 15.5;

        // For the harness: set a number by name ("weight3" for weight[3]). False if there's none of that name.
        bool set (const juce::String& name, double value);
    };
    Tuning& refinedTuning();   // the one in use (the harness changes it; nothing else does)

    // REFINED's look-ahead delay, in samples (as soothe 3's normal quality: 2304 up to 48 kHz, doubled per doubling).
    int lookaheadSamples (double sampleRate) noexcept;

    inline constexpr int maxBands = 8;
    inline constexpr double maxDepthDb = 18.0;   // a depth-curve band's range
    inline constexpr double maxCutLimitDb = 40.0;   // MAX CUT at the top: no limit

    // A band of the depth curve: boosting makes it work harder there,
    // cutting leaves that part alone. Band passes add up in parallel
    // (only their parts are worked on); the rest multiply.
    struct Band
    {
        bool used = false, on = true;
        Shape shape = Shape::bell;
        double frequency = 1000.0, depthDb = 0.0, q = 1.0;
        int slope = eq::defaultSlope;
        double focus = 0.0;   // -100 (left / mid only) to 100 (right / side only)
        bool isActive() const noexcept { return used && on; }
    };

    struct Settings
    {
        bool on = false;
        Engine engine = Engine::classic;
        bool lookahead = true;     // REFINED only
        Mode mode = Mode::soft;
        double depth = 5.0;        // 0 to 20
        double detail = 50.0;      // 0 to 100: broad build-ups to narrow resonances
        double attack = 50.0, release = 50.0;   // 0 to 100: fast to slow
        StereoMode stereo = StereoMode::midSide;
        double link = 100.0;       // %
        double focus = 0.0;        // -100 to 100
        double detailTiltLow = 0.0, detailTiltHigh = 0.0, attackTiltLow = 0.0, attackTiltHigh = 0.0,
               releaseTiltLow = 0.0, releaseTiltHigh = 0.0;   // -100 to 100
        double maxCutDb = maxCutLimitDb;
        double wetTrimDb = 0.0, mix = 100.0, outDb = 0.0;
        bool delta = false;
        std::array<Band, maxBands> bands {};
        int listenBand = -1;       // a band being listened to (its part of the delta), or -1
    };

    // The depth curve, in dB, at `hz` for channel 0 (left or mid) or 1 (right or side).
    double depthCurveDb (const Settings&, double hz, int channel, double sampleRate);

    // How the tilts weigh a frequency: 1 in the lows (below about 400 Hz)
    // fading to 0 by 1.2 kHz; 1 in the highs (above about 3 kHz) fading to 0 by 1 kHz.
    double lowWeight (double hz) noexcept;
    double highWeight (double hz) noexcept;

    class Processor
    {
    public:
        void prepare (double sampleRate, int maxBlockSize);
        void reset() noexcept;
        void process (juce::dsp::AudioBlock<float>, const Settings&) noexcept;

        // How late the sound comes out: REFINED's look-ahead, while on.
        int getLatencySamples (const Settings& s) const noexcept
        {
            return s.on && s.engine == Engine::refined && s.lookahead ? lookaheadSamples (sampleRate) : 0;
        }

        // For the display (any thread): the filters' frequencies and how far
        // each is cutting now, per channel (left/mid, right/side), in dB (0 or more).
        int getNumFilters() const noexcept { return numFilters; }
        double getFrequency (int filter) const noexcept { return frequencies[(size_t) filter]; }
        float getReductionDb (int channel, int filter) const noexcept { return shown[(size_t) juce::jlimit (0, 1, channel)][(size_t) filter].load(); }

        static constexpr int maxFilters = 128;

    private:
        struct Biquad { double b0 = 1, b1 = 0, b2 = 0, a1 = 0, a2 = 0; };
        struct State { double z1 = 0, z2 = 0; };
        static double tick (const Biquad& f, State& s, double x) noexcept
        {
            const auto y = f.b0 * x + s.z1;
            s.z1 = f.b1 * x - f.a1 * y + s.z2;
            s.z2 = f.b2 * x - f.a2 * y;
            return y;
        }

        void updateShape (const Settings&);      // detail and tilts: cut widths, overlaps, timing
        void updateCurve (const Settings&);      // the depth curve at each filter
        void computeTargets (const Settings&, int numChannels, double seconds) noexcept;
        // The work on a block: listen to `listen` (or the block itself), cut the block.
        void cutBlock (juce::dsp::AudioBlock<float> wet, const juce::AudioBuffer<float>* listen, const Settings&, bool delayed) noexcept;
        void blend (juce::dsp::AudioBlock<float> wet, const Settings&) noexcept;   // WET TRIM, MIX, DELTA, OUT (dry in `dry`)
        void processDelayed (juce::dsp::AudioBlock<float>, const Settings&) noexcept;   // REFINED with LOOK-AHEAD

        static constexpr int subBlock = 32;
        double sampleRate = 48000.0;
        int numFilters = 0;
        std::array<double, maxFilters> frequencies {};

        // Listening: the band passes, as plain arrays (one entry per filter)
        // so a sample goes through all of them side by side (0.22.2: the same
        // sums as one filter at a time, several at once). Their b1 is 0.
        std::array<double, maxFilters> detectorB0 {}, detectorB2 {}, detectorA1 {}, detectorA2 {};
        std::array<std::array<double, maxFilters>, 2> detectorZ1 {}, detectorZ2 {};
        std::array<std::array<double, maxFilters>, 2> power {};
        std::array<double, maxFilters> measure {};   // power smoothing per sample

        // Cutting
        std::array<double, maxFilters> cosW {}, alpha {}, attackSeconds {}, releaseSeconds {};
        // The reduction's smoothing for a sub-block of `smoothedFor` seconds
        // (1 - e^(-seconds / tau)), worked out when the timing or that changes.
        std::array<double, maxFilters> attackStep {}, releaseStep {};
        double smoothedFor = -1.0;
        std::array<int, maxFilters> windowHalf {};   // SOFT's neighbourhood, in filters either side
        std::array<double, maxFilters> marginDb {}, weight {}, detailScale {};   // REFINED: SOFT's margin, and where it works
        // The bells' overlap: how much of bell j's cut lands on filter k (k within reach of j).
        std::array<std::array<float, 2 * 48 + 1>, maxFilters> overlap {};
        int reach = 0;
        std::array<std::array<double, maxFilters>, 2> reduction {};   // the cut wanted, dB, smoothed
        std::array<std::array<double, maxFilters>, 2> gains {};       // each bell's gain, dB
        std::array<std::array<State, maxFilters>, 2> cutStates {};
        // The bells working now, gathered for one sub-block: each bell takes
        // the sample the bell before it finished on the step before, so all
        // of them work at once (a pipeline), each on the same samples, in the
        // same order, as one bell after another.
        std::array<Biquad, maxFilters> active {};
        std::array<State, maxFilters> activeStates {};
        std::array<int, maxFilters> activeIndex {};
        std::array<float, maxFilters + 1> pipe {};
        std::array<std::array<double, maxFilters>, 2> curve {};       // the depth curve, as a factor

        Settings shapedFor, curvedFor;
        bool shaped = false, curved = false;

        juce::AudioBuffer<float> dry, work;
        effects::BypassFade bypass;
        juce::SmoothedValue<float> mix, wetTrim, out;
        eq::Design listenDesign;
        std::array<std::array<std::array<double, 2>, eq::maxSections>, 2> listenStates {};
        int listening = -1;

        // REFINED's look-ahead: the input kept `latency` samples (`ahead`), the
        // bells' gains kept for the sub-blocks between hearing and cutting
        // (`queued`), the input as it came (`input`), and fading in and out
        // (it comes in once its delay has filled).
        int latency = 0, lagBlocks = 0, queueAt = 0, warm = 0;
        bool primed = false, wasDelayed = false;
        juce::AudioBuffer<float> ahead, input, heard;
        int aheadAt = 0;
        std::vector<std::array<std::array<double, maxFilters>, 2>> queued;
        std::array<std::array<double, maxFilters>, 2> applied {};
        juce::SmoothedValue<float> delayedFade;
        Engine engineFor = Engine::classic;

        std::array<std::array<std::atomic<float>, maxFilters>, 2> shown {};
    };
}
