#pragma once

#include <cstring>

#include <juce_audio_processors/juce_audio_processors.h>

// Redrawing only when what's drawn changes (0.22.2, the window's CPU): the
// rack units and the big pages' displays redrew themselves 30 times a second
// whether anything had moved or not, which took most of a core in software
// drawing. A ChangeWatch is a fingerprint of what a component draws: every
// parameter's value, plus whatever live readings the component adds (rounded
// as finely as it draws them). The timer redraws only when it changes.
class ChangeWatch
{
public:
    explicit ChangeWatch (juce::AudioProcessor& processor)
    {
        for (auto* parameter : processor.getParameters())
            parameters.push_back (parameter);
    }

    // Starts a new fingerprint: every parameter's value.
    ChangeWatch& begin()
    {
        hash = 14695981039346656037ull;
        for (const auto* parameter : parameters)
            add (parameter->getValue());
        return *this;
    }

    ChangeWatch& add (float value)
    {
        juce::uint32 bits = 0;
        std::memcpy (&bits, &value, sizeof (bits));
        return mix (bits);
    }
    ChangeWatch& add (int value) { return mix ((juce::uint64) (juce::uint32) value); }
    ChangeWatch& add (const juce::String& text) { return mix ((juce::uint64) text.hashCode64()); }

    // A live reading, rounded to `step` (a tenth of a dB, a hundredth...).
    ChangeWatch& add (float value, float step) { return add (juce::roundToInt (value / step)); }

    // True when the fingerprint differs from the last one (the first time,
    // always); remembers it.
    bool changed() noexcept
    {
        const auto result = first || hash != last;
        first = false;
        last = hash;
        return result;
    }

    // The next changed() says true (after something drawn outside the
    // fingerprint changed, such as a component's size).
    void forget() noexcept { first = true; }

private:
    ChangeWatch& mix (juce::uint64 value)
    {
        hash ^= value;
        hash *= 1099511628211ull;   // FNV-1a
        return *this;
    }

    std::vector<juce::AudioProcessorParameter*> parameters;
    juce::uint64 hash = 0, last = 0;
    bool first = true;
};
