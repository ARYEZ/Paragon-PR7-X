#include "Dominion.h"

namespace dominion
{
    namespace
    {
        constexpr double pi = juce::MathConstants<double>::pi;
        constexpr double spacingOctaves = 1.0 / 12.0;
        constexpr double detectorQ = 8.65;   // a 1/6-octave band pass
        constexpr double floorBelowLoudestDb = 60.0, floorDb = -100.0;
        constexpr double softMarginDb = 2.0, kneeDb = 3.0;
        constexpr int nearExcluded = 2;
        constexpr double maxReductionDb = 40.0;

        double smoothstep (double x) noexcept
        {
            x = juce::jlimit (0.0, 1.0, x);
            return x * x * (3.0 - 2.0 * x);
        }

        // Soft knee over `kneeDb` round 0: nothing below, then a dB per dB.
        double softKnee (double over) noexcept
        {
            const auto half = 0.5 * kneeDb;
            return over <= -half ? 0.0 : over < half ? (over + half) * (over + half) / (2.0 * kneeDb) : over;
        }

        // The width of a cut at a DETAIL (0 to 100), in octaves to half its depth.
        double widthFor (double detail) noexcept
        {
            return std::pow (2.0, juce::jmap (juce::jlimit (0.0, 100.0, detail) / 100.0, std::log2 (0.5), std::log2 (1.0 / 16.0)));
        }

        double qForWidth (double octaves) noexcept
        {
            const auto ratio = std::pow (2.0, octaves);
            return std::sqrt (ratio) / (ratio - 1.0);
        }

        eq::Band toEq (const Band& band)
        {
            eq::Band b;
            b.used = band.used;
            b.on = band.on;
            b.frequency = band.frequency;
            b.q = band.q;
            b.slope = band.slope;
            b.gainDb = band.depthDb;
            switch (band.shape)
            {
                case Shape::lowCut:     b.shape = eq::Shape::lowCut; break;
                case Shape::lowShelf:   b.shape = eq::Shape::lowShelf; break;
                case Shape::highShelf:  b.shape = eq::Shape::highShelf; break;
                case Shape::highCut:    b.shape = eq::Shape::highCut; break;
                case Shape::bell:       b.shape = eq::Shape::bell; break;
                case Shape::bandPass:   b.shape = eq::Shape::bandPass; break;
                case Shape::bandReject: b.shape = eq::Shape::notch; break;
                case Shape::tilt:       b.shape = eq::Shape::tiltShelf; break;
            }
            return b;
        }

        // A band's (or FOCUS's) weight on channel 0 or 1: -100 all on 0, 100 all on 1.
        double focusWeight (double focus, int channel) noexcept
        {
            return channel == 0 ? juce::jlimit (0.0, 1.0, 1.0 - focus / 100.0) : juce::jlimit (0.0, 1.0, 1.0 + focus / 100.0);
        }
    }

    namespace
    {
        // Between three points (at 0, 50 and 100), on a log scale.
        double between3 (double at, double v0, double v50, double v100) noexcept
        {
            at = juce::jlimit (0.0, 100.0, at);
            return at < 50.0 ? v0 * std::pow (v50 / v0, at / 50.0) : v50 * std::pow (v100 / v50, (at - 50.0) / 50.0);
        }

        // Between four points (at 0, 25, 50 and 100), on a log scale.
        double between4 (double at, double v0, double v25, double v50, double v100) noexcept
        {
            at = juce::jlimit (0.0, 100.0, at);
            return at < 25.0 ? v0 * std::pow (v25 / v0, at / 25.0)
                 : at < 50.0 ? v25 * std::pow (v50 / v25, (at - 25.0) / 25.0)
                             : v50 * std::pow (v100 / v50, (at - 50.0) / 50.0);
        }

        double kneeOver (double over, double knee) noexcept
        {
            const auto half = 0.5 * knee;
            return over <= -half ? 0.0 : over < half ? (over + half) * (over + half) / (2.0 * knee) : over;
        }
    }

    Tuning& refinedTuning()
    {
        static Tuning tuning;
        return tuning;
    }

    bool Tuning::set (const juce::String& name, double value)
    {
        const std::pair<const char*, double*> named[] = {
            { "depthStart", &depthStart }, { "depthPower", &depthPower }, { "depthScale", &depthScale },
            { "margin0", &margin0 }, { "margin100", &margin100 }, { "knee", &knee },
            { "marginDepth", &marginDepth }, { "overPower", &overPower }, { "detailScale0", &detailScale0 }, { "detailScale100", &detailScale100 },
            { "width0", &width0 }, { "width50", &width50 }, { "width100", &width100 },
            { "window0", &window0 }, { "window100", &window100 },
            { "attack0", &attack0 }, { "attack25", &attack25 }, { "attack50", &attack50 }, { "attack100", &attack100 },
            { "release0", &release0 }, { "release50", &release50 }, { "release100", &release100 },
            { "timingPower", &timingPower }, { "hardAttack", &hardAttack }, { "hardRelease", &hardRelease },
            { "detailAttack0", &detailAttack0 }, { "detailAttack100", &detailAttack100 },
            { "detailRelease0", &detailRelease0 }, { "detailRelease100", &detailRelease100 },
            { "hard5", &hard5 }, { "hardStep", &hardStep }, { "hardSlope", &hardSlope }, { "hardTilt", &hardTilt },
            { "hardCurve", &hardCurve }, { "hardFlat", &hardFlat }, { "hardKnee", &hardKnee },
            { "cycles", &cycles }, { "leadMs", &leadMs } };
        for (const auto& [n, target] : named)
            if (name == n)
            {
                *target = value;
                return true;
            }
        if (name.startsWith ("weight"))
        {
            const auto i = name.substring (6).getIntValue();
            if (i >= 0 && i < (int) weight.size() && name.substring (6).containsOnly ("0123456789"))
            {
                weight[(size_t) i] = value;
                return true;
            }
        }
        return false;
    }

    int lookaheadSamples (double sampleRate) noexcept
    {
        return sampleRate <= 50000.0 ? 2304 : sampleRate <= 100000.0 ? 4704 : 9408;
    }

    double lowWeight (double hz) noexcept  { return smoothstep (std::log2 (1200.0 / hz) / std::log2 (1200.0 / 400.0)); }
    double highWeight (double hz) noexcept { return smoothstep (std::log2 (hz / 1000.0) / std::log2 (3000.0 / 1000.0)); }

    double depthCurveDb (const Settings& settings, double hz, int channel, double sampleRate)
    {
        double total = 0.0, parallel = 0.0;
        auto anyBandPass = false;
        for (const auto& band : settings.bands)
        {
            if (! band.isActive())
                continue;
            const auto db = focusWeight (band.focus, channel) * eq::responseDb (eq::design (toEq (band), sampleRate), hz, sampleRate);
            if (band.shape == Shape::bandPass)
            {
                anyBandPass = true;
                parallel += std::pow (10.0, db / 20.0);
            }
            else
            {
                total += db;
            }
        }
        if (anyBandPass)
            total += 20.0 * std::log10 (std::max (parallel, 1.0e-6));
        return juce::jlimit (-120.0, 24.0, total);
    }

    //==========================================================================
    void Processor::prepare (double newSampleRate, int maxBlockSize)
    {
        sampleRate = newSampleRate;
        numFilters = 0;
        for (auto hz = 20.0; hz <= std::min (20000.0, 0.45 * sampleRate) && numFilters < maxFilters; hz *= std::pow (2.0, spacingOctaves))
            frequencies[(size_t) numFilters++] = hz;

        for (int k = 0; k < numFilters; ++k)
        {
            const auto w = 2.0 * pi * frequencies[(size_t) k] / sampleRate;
            const auto a = std::sin (w) / (2.0 * detectorQ), a0 = 1.0 + a;
            detectorB0[(size_t) k] = a / a0;
            detectorB2[(size_t) k] = -a / a0;
            detectorA1[(size_t) k] = -2.0 * std::cos (w) / a0;
            detectorA2[(size_t) k] = (1.0 - a) / a0;
            cosW[(size_t) k] = std::cos (w);
        }
        dry.setSize (2, maxBlockSize);
        work.setSize (2, maxBlockSize);
        input.setSize (2, maxBlockSize);
        heard.setSize (2, subBlock);
        latency = lookaheadSamples (sampleRate);
        ahead.setSize (2, latency + 1);
        queued.assign ((size_t) (latency / subBlock + 2), {});
        delayedFade.reset (sampleRate, 0.02);
        primed = false;
        bypass.prepare (sampleRate, maxBlockSize);
        for (auto* smoothed : { &mix, &wetTrim, &out })
            smoothed->reset (sampleRate, 0.02);
        shaped = curved = false;
        reset();
    }

    void Processor::reset() noexcept
    {
        detectorZ1 = {};
        detectorZ2 = {};
        power = {};
        reduction = {};
        gains = {};
        cutStates = {};
        listenStates = {};
        listening = -1;
        applied = {};
        for (auto& q : queued)
            q = {};
        queueAt = 0;
        ahead.clear();
        aheadAt = 0;
        warm = 0;
        for (auto& channel : shown)
            for (auto& value : channel)
                value.store (0.0f);
    }

    void Processor::updateShape (const Settings& s)
    {
        // Per filter: DETAIL with its tilts, the cut's width, SOFT's neighbourhood, and the timing.
        const auto refined = s.engine == Engine::refined;
        const auto& t = refinedTuning();
        auto widest = 0.0;
        std::array<double, maxFilters> q {};
        for (int k = 0; k < numFilters; ++k)
        {
            const auto hz = frequencies[(size_t) k];
            const auto low = lowWeight (hz), high = highWeight (hz);
            const auto detail = juce::jlimit (0.0, 100.0, s.detail + 0.5 * (s.detailTiltLow * low + s.detailTiltHigh * high));
            const auto attackTilt = std::pow (4.0, (s.attackTiltLow * low + s.attackTiltHigh * high) / 100.0);
            const auto releaseTilt = std::pow (4.0, (s.releaseTiltLow * low + s.releaseTiltHigh * high) / 100.0);
            if (! refined)
            {
                const auto width = widthFor (detail);
                widest = std::max (widest, width);
                q[(size_t) k] = qForWidth (width);
                windowHalf[(size_t) k] = std::max (nearExcluded + 2, (int) std::round (juce::jmap (detail / 100.0, 1.0, 1.0 / 3.0) / spacingOctaves));

                // ATTACK 5 ms and RELEASE 60 ms at 1 kHz at 50%, a quarter to four
                // times that from 0 to 100%, quicker up high and slower down low;
                // the tilts slow (up) or speed (down) the lows and highs.
                const auto byFrequency = std::sqrt (1000.0 / hz);
                attackSeconds[(size_t) k] = juce::jlimit (0.0002, 0.3, 0.005 * std::pow (4.0, (s.attack - 50.0) / 50.0) * byFrequency * attackTilt);
                releaseSeconds[(size_t) k] = juce::jlimit (0.005, 3.0, 0.06 * std::pow (4.0, (s.release - 50.0) / 50.0) * byFrequency * releaseTilt);
                // The level over about 16 cycles (4 to 120 ms): steady enough that
                // noise's own flicker doesn't read as resonances.
                measure[(size_t) k] = 1.0 - std::exp (-1.0 / (juce::jlimit (0.004, 0.12, 16.0 / hz) * sampleRate));
            }
            else
            {
                const auto width = between3 (detail, t.width0, t.width50, t.width100);
                widest = std::max (widest, width);
                q[(size_t) k] = qForWidth (width);
                windowHalf[(size_t) k] = std::max (nearExcluded + 2, (int) std::round (juce::jmap (detail / 100.0, t.window0, t.window100) / spacingOctaves));
                marginDb[(size_t) k] = juce::jmap (detail / 100.0, t.margin0, t.margin100);
                detailScale[(size_t) k] = between3 (detail, t.detailScale0, 1.0, t.detailScale100);

                const auto byFrequency = std::pow (1000.0 / hz, t.timingPower);
                const auto hard = s.mode == Mode::hard;
                attackSeconds[(size_t) k] = juce::jlimit (0.0002, 2.0, 0.001 * between4 (s.attack, t.attack0, t.attack25, t.attack50, t.attack100)
                                                                          * between3 (detail, t.detailAttack0, 1.0, t.detailAttack100) * byFrequency * attackTilt
                                                                          * (hard ? t.hardAttack : 1.0));
                releaseSeconds[(size_t) k] = juce::jlimit (0.002, 6.0, 0.001 * between3 (s.release, t.release0, t.release50, t.release100)
                                                                           * between3 (detail, t.detailRelease0, 1.0, t.detailRelease100) * byFrequency * releaseTilt
                                                                           * (hard ? t.hardRelease : 1.0));
                measure[(size_t) k] = 1.0 - std::exp (-1.0 / (juce::jlimit (0.004, 0.12, t.cycles / hz) * sampleRate));

                // Where it works: the weights an octave apart from 25 Hz, in between on a log scale.
                const auto at = juce::jlimit (0.0, (double) t.weight.size() - 1.0, std::log2 (hz / 25.0));
                const auto i = std::min ((int) at, (int) t.weight.size() - 2);
                weight[(size_t) k] = std::max (0.0, t.weight[(size_t) i] + (t.weight[(size_t) i + 1] - t.weight[(size_t) i]) * (at - i));
            }
            alpha[(size_t) k] = std::sin (2.0 * pi * hz / sampleRate) / (2.0 * q[(size_t) k]);
        }

        // How the bells overlap: bell j's cut, in dB, falls off as a band
        // pass's power does (1 / (1 + Q^2 (r - 1/r)^2)): far enough to matter
        // until it's down to 2%.
        const auto qWidest = qForWidth (widest);
        const auto r = (1.0 / qWidest) * std::sqrt (1.0 / 0.02 - 1.0);   // r - 1/r there
        const auto ratio = 0.5 * (r + std::sqrt (r * r + 4.0));
        reach = juce::jlimit (1, 48, (int) std::ceil (std::log2 (ratio) / spacingOctaves));
        for (int k = 0; k < numFilters; ++k)
            for (int offset = -reach; offset <= reach; ++offset)
            {
                const auto j = k + offset;
                auto& value = overlap[(size_t) k][(size_t) (offset + reach)];
                if (j < 0 || j >= numFilters)
                {
                    value = 0.0f;
                    continue;
                }
                const auto x = frequencies[(size_t) k] / frequencies[(size_t) j];
                const auto d = q[(size_t) j] * (x - 1.0 / x);
                value = (float) (1.0 / (1.0 + d * d));
            }

        shapedFor = s;
        shaped = true;
        smoothedFor = -1.0;   // the timing changed: its steps are worked out again
    }

    void Processor::updateCurve (const Settings& s)
    {
        for (int channel = 0; channel < 2; ++channel)
        {
            const auto focus = focusWeight (s.focus, channel);
            for (int k = 0; k < numFilters; ++k)
                curve[(size_t) channel][(size_t) k] = focus * std::pow (10.0, depthCurveDb (s, frequencies[(size_t) k], channel, sampleRate) / 20.0);
        }
        curvedFor = s;
        curved = true;
    }

    void Processor::computeTargets (const Settings& s, int numChannels, double seconds) noexcept
    {
        // Each part's level, in dB (a sine in the middle of a part reads its
        // own level), and with LINK, part of the way to both channels together.
        std::array<std::array<double, maxFilters>, 2> level {};
        auto loudest = floorDb;
        for (int k = 0; k < numFilters; ++k)
        {
            const auto both = 10.0 * std::log10 (power[0][(size_t) k] + (numChannels > 1 ? power[1][(size_t) k] : power[0][(size_t) k]) + 1.0e-30);
            for (int c = 0; c < numChannels; ++c)
            {
                const auto own = 10.0 * std::log10 (2.0 * power[(size_t) c][(size_t) k] + 1.0e-30);
                const auto linked = numChannels > 1 ? own + (both - own) * s.link / 100.0 : own;
                level[(size_t) c][(size_t) k] = linked;
                loudest = std::max (loudest, linked);
            }
        }

        const auto depthFactor = juce::jlimit (0.0, 20.0, s.depth) / 5.0;
        // HARD's fixed level: -20 dB per part at DEPTH 0, 3 dB lower for each
        // step (-35 at 5; a mix's parts mostly sit at -30 to -50).
        const auto hardThreshold = -20.0 - 3.0 * juce::jlimit (0.0, 20.0, s.depth);
        const auto maxCut = juce::jlimit (0.0, maxReductionDb, s.maxCutDb);
        // REFINED: DEPTH's scale, and HARD's level.
        const auto refined = s.engine == Engine::refined;
        const auto& tuning = refinedTuning();
        const auto depth = juce::jlimit (0.0, 20.0, s.depth);
        const auto refinedDepth = tuning.depthScale * std::pow (std::max (0.0, depth - tuning.depthStart) / (5.0 - tuning.depthStart), tuning.depthPower);
        const auto refinedHard = tuning.hard5 - tuning.hardStep * (depth - 5.0) - tuning.hardCurve * (depth - 5.0) * std::abs (depth - 5.0);
        const auto refinedMargin = tuning.marginDepth * (depth - 5.0);
        if (! juce::exactlyEqual (seconds, smoothedFor))
        {
            for (int k = 0; k < numFilters; ++k)
            {
                attackStep[(size_t) k] = 1.0 - std::exp (-seconds / attackSeconds[(size_t) k]);
                releaseStep[(size_t) k] = 1.0 - std::exp (-seconds / releaseSeconds[(size_t) k]);
            }
            smoothedFor = seconds;
        }
        for (int c = 0; c < numChannels; ++c)
        {
            const auto& e = level[(size_t) c];
            // Running sums, for each part's neighbourhood average.
            std::array<double, maxFilters + 1> sums {};
            for (int k = 0; k < numFilters; ++k)
                sums[(size_t) k + 1] = sums[(size_t) k] + e[(size_t) k];

            for (int k = 0; k < numFilters; ++k)
            {
                double target = 0.0;
                if (refined)
                {
                    if (e[(size_t) k] > loudest - floorBelowLoudestDb && e[(size_t) k] > floorDb)
                    {
                        if (s.mode == Mode::soft)
                        {
                            const auto from = std::max (0, k - windowHalf[(size_t) k]), to = std::min (numFilters - 1, k + windowHalf[(size_t) k]);
                            const auto nearFrom = std::max (from, k - nearExcluded), nearTo = std::min (to, k + nearExcluded);
                            const auto count = (to - from + 1) - (nearTo - nearFrom + 1);
                            const auto around = count > 0 ? ((sums[(size_t) to + 1] - sums[(size_t) from]) - (sums[(size_t) nearTo + 1] - sums[(size_t) nearFrom])) / count
                                                          : e[(size_t) k];
                            target = refinedDepth * detailScale[(size_t) k] * weight[(size_t) k]
                                   * std::pow (kneeOver (e[(size_t) k] - around - marginDb[(size_t) k] + refinedMargin, tuning.knee), tuning.overPower);
                        }
                        else
                        {
                            const auto tilted = e[(size_t) k] + tuning.hardTilt * std::log2 (frequencies[(size_t) k] / 1000.0);
                            target = tuning.hardSlope * (tuning.hardFlat + (1.0 - tuning.hardFlat) * weight[(size_t) k])
                                   * kneeOver (tilted - refinedHard, tuning.hardKnee);
                        }
                    }
                }
                else if (e[(size_t) k] > loudest - floorBelowLoudestDb && e[(size_t) k] > floorDb)
                {
                    if (s.mode == Mode::soft)
                    {
                        // The parts around it, leaving out its nearest two either
                        // side (they hear a resonance too, and would raise the bar).
                        const auto from = std::max (0, k - windowHalf[(size_t) k]), to = std::min (numFilters - 1, k + windowHalf[(size_t) k]);
                        const auto nearFrom = std::max (from, k - nearExcluded), nearTo = std::min (to, k + nearExcluded);
                        const auto count = (to - from + 1) - (nearTo - nearFrom + 1);
                        const auto around = count > 0 ? ((sums[(size_t) to + 1] - sums[(size_t) from]) - (sums[(size_t) nearTo + 1] - sums[(size_t) nearFrom])) / count
                                                      : e[(size_t) k];
                        target = depthFactor * softKnee (e[(size_t) k] - around - softMarginDb);
                    }
                    else
                    {
                        // HARD: over a fixed level, tilted up 1.5 dB an octave
                        // (music has more in the lows), at 2:1.
                        const auto tilted = e[(size_t) k] + 1.5 * std::log2 (frequencies[(size_t) k] / 1000.0);
                        target = 0.5 * softKnee (tilted - hardThreshold);
                    }
                }
                target = std::min (target * curve[(size_t) c][(size_t) k], maxCut);

                auto& r = reduction[(size_t) c][(size_t) k];
                r += (target - r) * (target > r ? attackStep[(size_t) k] : releaseStep[(size_t) k]);
            }

        }

        // Each bell's gain so that, overlapping, they cut what's wanted:
        // a few Gauss-Seidel passes (kept to cuts), carried on from last time.
        // The channels are solved side by side (each its own sums, in the
        // same order as on its own), so one's sums run while the other's wait.
        for (int pass = 0; pass < 3; ++pass)
            for (int j = 0; j < numFilters; ++j)
            {
                const auto& row = overlap[(size_t) j];
                // The bells in reach (those past either end aren't there).
                const auto first = std::max (-reach, -j), last = std::min (reach, numFilters - 1 - j);
                auto& g0 = gains[0];
                if (numChannels > 1)
                {
                    auto& g1 = gains[1];
                    double sum0 = 0.0, sum1 = 0.0;
                    for (int offset = first; offset <= last; ++offset)
                    {
                        const auto weight = (double) row[(size_t) (offset + reach)];
                        sum0 += weight * g0[(size_t) (j + offset)];
                        sum1 += weight * g1[(size_t) (j + offset)];
                    }
                    g0[(size_t) j] = std::max (0.0, g0[(size_t) j] + reduction[0][(size_t) j] - sum0);
                    g1[(size_t) j] = std::max (0.0, g1[(size_t) j] + reduction[1][(size_t) j] - sum1);
                }
                else
                {
                    double sum0 = 0.0;
                    for (int offset = first; offset <= last; ++offset)
                        sum0 += (double) row[(size_t) (offset + reach)] * g0[(size_t) (j + offset)];
                    g0[(size_t) j] = std::max (0.0, g0[(size_t) j] + reduction[0][(size_t) j] - sum0);
                }
            }
    }

    void Processor::process (juce::dsp::AudioBlock<float> block, const Settings& s) noexcept
    {
        const auto numChannels = (int) juce::jmin ((size_t) 2, block.getNumChannels());
        const auto numSamples = (int) block.getNumSamples();
        if (numChannels == 0 || numSamples == 0 || numFilters == 0)
            return;

        // REFINED with LOOK-AHEAD runs late, and fades in and out its own way.
        const auto delayedPath = s.engine == Engine::refined && s.lookahead;
        if (delayedPath != wasDelayed)
        {
            wasDelayed = delayedPath;
            primed = false;
            reset();
        }
        if (delayedPath)
        {
            if (! s.on && ! delayedFade.isSmoothing() && delayedFade.getCurrentValue() <= 0.0f)
            {
                primed = false;   // starting again later: from a clean start, once the delay has filled
                for (auto& channel : shown)
                    for (auto& value : channel)
                        value.store (0.0f);
                return;
            }
            if (! primed)
            {
                reset();
                primed = true;
                delayedFade.setCurrentAndTargetValue (0.0f);
            }
        }
        else
        {
            if (bypass.isSilent() && ! s.on)
            {
                for (auto& channel : shown)
                    for (auto& value : channel)
                        value.store (0.0f);
                return;
            }
            if (bypass.isSilent())
                reset();   // coming back on: from a clean start
        }

        // Only redone when what they depend on has changed at all.
        const auto moved = [] (double a, double b) { return ! juce::exactlyEqual (a, b); };
        if (s.engine != engineFor)
        {
            engineFor = s.engine;   // another engine: from a clean start
            shaped = false;
            reset();
        }
        const auto shapeChanged = ! shaped || s.engine != shapedFor.engine || (s.engine == Engine::refined && s.mode != shapedFor.mode) || moved (s.detail, shapedFor.detail) || moved (s.attack, shapedFor.attack)
                               || moved (s.release, shapedFor.release)
                               || moved (s.detailTiltLow, shapedFor.detailTiltLow) || moved (s.detailTiltHigh, shapedFor.detailTiltHigh)
                               || moved (s.attackTiltLow, shapedFor.attackTiltLow) || moved (s.attackTiltHigh, shapedFor.attackTiltHigh)
                               || moved (s.releaseTiltLow, shapedFor.releaseTiltLow) || moved (s.releaseTiltHigh, shapedFor.releaseTiltHigh);
        if (shapeChanged)
            updateShape (s);
        auto curveChanged = ! curved || moved (s.focus, curvedFor.focus);
        for (size_t i = 0; i < s.bands.size() && ! curveChanged; ++i)
        {
            const auto& a = s.bands[i];
            const auto& b = curvedFor.bands[i];
            curveChanged = a.used != b.used || a.on != b.on || a.shape != b.shape || moved (a.frequency, b.frequency)
                        || moved (a.depthDb, b.depthDb) || moved (a.q, b.q) || a.slope != b.slope || moved (a.focus, b.focus);
        }
        if (curveChanged)
            updateCurve (s);

        mix.setTargetValue ((float) juce::jlimit (0.0, 1.0, s.mix / 100.0));
        wetTrim.setTargetValue ((float) juce::Decibels::decibelsToGain (s.wetTrimDb));
        out.setTargetValue ((float) juce::Decibels::decibelsToGain (s.outDb));

        // Listening to one band's part of what's taken away.
        const auto listen = s.listenBand >= 0 && s.listenBand < maxBands && s.bands[(size_t) s.listenBand].used ? s.listenBand : -1;
        if (listen != listening)
        {
            listening = listen;
            listenStates = {};
            if (listen >= 0)
                listenDesign = eq::soloDesign (toEq (s.bands[(size_t) listen]), sampleRate);
        }

        if (delayedPath)
        {
            processDelayed (block.getSubsetChannelBlock (0, (size_t) numChannels), s);
        }
        else
        {
            bypass.process (block.getSubsetChannelBlock (0, (size_t) numChannels), s.on, [&] (juce::dsp::AudioBlock<float> wet)
            {
                for (int c = 0; c < numChannels; ++c)
                    dry.copyFrom (c, 0, wet.getChannelPointer ((size_t) c), numSamples);
                cutBlock (wet, nullptr, s, false);
                blend (wet, s);
            });
        }

        // For the display: the cut, scaled by MIX.
        const auto shownMix = (float) juce::jlimit (0.0, 1.0, s.mix / 100.0);
        for (int c = 0; c < 2; ++c)
            for (int k = 0; k < numFilters; ++k)
                shown[(size_t) c][(size_t) k].store (s.on && c < numChannels ? (float) reduction[(size_t) c][(size_t) k] * shownMix : 0.0f);
    }

    void Processor::processDelayed (juce::dsp::AudioBlock<float> block, const Settings& s) noexcept
    {
        const auto numChannels = (int) block.getNumChannels();
        const auto numSamples = (int) block.getNumSamples();
        lagBlocks = juce::jlimit (0, (int) queued.size() - 1,
                                  (int) std::lround ((latency - refinedTuning().leadMs * 0.001 * sampleRate) / subBlock));

        // The sound as it comes (heard now), and as it was `latency` samples
        // ago (cut now, and the dry for MIX and DELTA).
        const auto size = latency + 1;
        for (int c = 0; c < numChannels; ++c)
            input.copyFrom (c, 0, block.getChannelPointer ((size_t) c), numSamples);
        for (int i = 0; i < numSamples; ++i)
        {
            const auto from = (aheadAt + 1) % size;
            for (int c = 0; c < numChannels; ++c)
            {
                ahead.setSample (c, aheadAt, input.getSample (c, i));
                block.setSample (c, i, ahead.getSample (c, from));
            }
            aheadAt = from;
        }
        for (int c = 0; c < numChannels; ++c)
            dry.copyFrom (c, 0, block.getChannelPointer ((size_t) c), numSamples);

        cutBlock (block, &input, s, true);
        blend (block, s);

        // In once the delay has filled (until then the sound passes as it
        // comes), out when switched off; 20 ms fades.
        delayedFade.setTargetValue (s.on && warm >= latency ? 1.0f : 0.0f);
        warm = std::min (latency, warm + numSamples);
        if (delayedFade.isSmoothing() || delayedFade.getCurrentValue() < 1.0f)
            for (int i = 0; i < numSamples; ++i)
            {
                const auto amount = delayedFade.getNextValue();
                for (int c = 0; c < numChannels; ++c)
                    block.setSample (c, i, input.getSample (c, i) + (block.getSample (c, i) - input.getSample (c, i)) * amount);
            }
    }

    void Processor::cutBlock (juce::dsp::AudioBlock<float> wet, const juce::AudioBuffer<float>* listen, const Settings& s, bool delayed) noexcept
    {
        const auto numChannels = (int) juce::jmin ((size_t) 2, wet.getNumChannels());
        const auto numSamples = (int) wet.getNumSamples();
        const auto midSide = s.stereo == StereoMode::midSide && numChannels == 2;
        for (int start = 0; start < numSamples; start += subBlock)
        {
            const auto count = std::min (subBlock, numSamples - start);

            // Into left/right or mid/side.
            for (int i = 0; i < count; ++i)
            {
                const auto l = wet.getSample (0, start + i);
                const auto r = numChannels > 1 ? wet.getSample (1, start + i) : l;
                work.setSample (0, i, midSide ? 0.5f * (l + r) : l);
                if (numChannels > 1)
                    work.setSample (1, i, midSide ? 0.5f * (l - r) : r);
            }

            // With LOOK-AHEAD, listening to the sound as it comes in
            // (`listen`) while cutting it as it was (the block).
            if (listen != nullptr)
                for (int i = 0; i < count; ++i)
                {
                    const auto l = listen->getSample (0, start + i);
                    const auto r = numChannels > 1 ? listen->getSample (1, start + i) : l;
                    heard.setSample (0, i, midSide ? 0.5f * (l + r) : l);
                    if (numChannels > 1)
                        heard.setSample (1, i, midSide ? 0.5f * (l - r) : r);
                }

            // Listen: each sample through every band pass at once (they
            // don't depend on each other). b1 is 0, so z1 is z2 - a1 y.
            for (int c = 0; c < numChannels; ++c)
            {
                const auto* x = (listen != nullptr ? heard : work).getReadPointer (c);
                auto* z1 = detectorZ1[(size_t) c].data();
                auto* z2 = detectorZ2[(size_t) c].data();
                auto* p = power[(size_t) c].data();
                const auto* b0 = detectorB0.data();
                const auto* b2 = detectorB2.data();
                const auto* a1 = detectorA1.data();
                const auto* a2 = detectorA2.data();
                const auto* m = measure.data();
                for (int i = 0; i < count; ++i)
                {
                    const auto in = (double) x[i];
                    for (int k = 0; k < numFilters; ++k)
                    {
                        const auto y = b0[k] * in + z1[k];
                        z1[k] = z2[k] - a1[k] * y;
                        z2[k] = b2[k] * in - a2[k] * y;
                        p[k] += m[k] * (y * y - p[k]);
                    }
                }
            }
            computeTargets (s, numChannels, count / sampleRate);

            // With LOOK-AHEAD, the gains heard `lagBlocks` sub-blocks ago
            // (the cut sees `leadMs` ahead of the sound it cuts).
            auto* use = &gains;
            if (delayed && lagBlocks > 0)
            {
                const auto size = (int) queued.size();
                queued[(size_t) queueAt] = gains;
                applied = queued[(size_t) ((queueAt - lagBlocks + size) % size)];
                queueAt = (queueAt + 1) % size;
                use = &applied;
            }

            // Cut: each bell, redesigned for its gain, in series.
            for (int c = 0; c < numChannels; ++c)
            {
                auto* x = work.getWritePointer (c);
                int numActive = 0;
                for (int k = 0; k < numFilters; ++k)
                {
                    auto& gain = (*use)[(size_t) c][(size_t) k];
                    auto& state = cutStates[(size_t) c][(size_t) k];
                    if (gain < 0.002)
                    {
                        // Doing nothing: once its memory has died away, skip it
                        // (a flat bell with an empty memory stays empty).
                        gain = 0.0;
                        if (std::abs (state.z1) < 1.0e-12 && std::abs (state.z2) < 1.0e-12)
                        {
                            state = {};
                            continue;
                        }
                    }
                    const auto A = std::pow (10.0, -gain / 40.0), a = alpha[(size_t) k], cw = cosW[(size_t) k];
                    const auto a0 = 1.0 + a / A;
                    active[(size_t) numActive] = { (1.0 + a * A) / a0, -2.0 * cw / a0, (1.0 - a * A) / a0, -2.0 * cw / a0, (1.0 - a / A) / a0 };
                    activeStates[(size_t) numActive] = state;
                    activeIndex[(size_t) numActive++] = k;
                }

                // The bells in series as a pipeline: on step t, bell j works
                // on sample t - j, taking what bell j - 1 finished on the
                // step before (from the back, so it isn't overwritten
                // first). Each value is a float between bells, as before.
                if (numActive > 0)
                {
                    for (int t = 0; t < count + numActive - 1; ++t)
                    {
                        const auto lastBell = std::min (numActive - 1, t), firstBell = std::max (0, t - count + 1);
                        if (t < count)
                            pipe[0] = x[t];
                        for (int j = lastBell; j >= firstBell; --j)
                            pipe[(size_t) j + 1] = (float) tick (active[(size_t) j], activeStates[(size_t) j], pipe[(size_t) j]);
                        if (t >= numActive - 1)
                            x[t - (numActive - 1)] = pipe[(size_t) numActive];
                    }
                    for (int j = 0; j < numActive; ++j)
                        cutStates[(size_t) c][(size_t) activeIndex[(size_t) j]] = activeStates[(size_t) j];
                }
            }

            // Back to left/right.
            for (int i = 0; i < count; ++i)
            {
                const auto a = work.getSample (0, i);
                const auto b = numChannels > 1 ? work.getSample (1, i) : a;
                wet.setSample (0, start + i, midSide ? a + b : a);
                if (numChannels > 1)
                    wet.setSample (1, start + i, midSide ? a - b : b);
            }
        }
    }

    void Processor::blend (juce::dsp::AudioBlock<float> wet, const Settings& s) noexcept
    {
        const auto numChannels = (int) juce::jmin ((size_t) 2, wet.getNumChannels());
        const auto numSamples = (int) wet.getNumSamples();
        // WET TRIM, MIX, DELTA (or one band's part of it), OUT.
        for (int i = 0; i < numSamples; ++i)
        {
            const auto trim = wetTrim.getNextValue(), amount = mix.getNextValue(), gain = out.getNextValue();
            for (int c = 0; c < numChannels; ++c)
            {
                const auto d = dry.getSample (c, i);
                const auto mixed = d + (wet.getSample (c, i) * trim - d) * amount;
                double y = mixed;
                if (listening >= 0)
                {
                    auto value = (double) (d - mixed);
                    for (int section = 0; section < listenDesign.numSections; ++section)
                    {
                        const auto& q = listenDesign.sections[(size_t) section];
                        auto& z = listenStates[(size_t) c][(size_t) section];
                        const auto out0 = q.b0 * value + z[0];
                        z[0] = q.b1 * value - q.a1 * out0 + z[1];
                        z[1] = q.b2 * value - q.a2 * out0;
                        value = out0;
                    }
                    y = value * listenDesign.gain;
                }
                else if (s.delta)
                {
                    y = d - mixed;
                }
                wet.setSample (c, i, (float) y * gain);
            }
        }
    }
}
