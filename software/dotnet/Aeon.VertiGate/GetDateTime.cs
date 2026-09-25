using Bonsai;
using Bonsai.Harp;
using System;
using System.ComponentModel;
using System.Linq;
using System.Reactive.Linq;

namespace Aeon.VertiGate
{
    /// <summary>
    /// Represents an operator that converts a Harp timestamp into a date and time.
    /// </summary>
    /// <remarks>
    /// Harp counts seconds from 1904-01-01 00:00:00 UTC. A device reports the time
    /// of its own clock, which starts at zero on power up. Until a controller sets
    /// the clock, the date reads as 1904. That is not a fault: it tells you the
    /// device clock is not synchronised.
    /// <para>
    /// This operator is not generated from <c>device.yml</c>. Neither Bonsai.Harp
    /// nor any Harp device package converts a Harp timestamp to a date, so each
    /// library that needs one writes its own.
    /// </para>
    /// </remarks>
    [Combinator]
    [WorkflowElementCategory(ElementCategory.Transform)]
    [Description("Converts a Harp timestamp into a date and time.")]
    public class GetDateTime
    {
        /// <summary>
        /// The instant from which Harp counts seconds.
        /// </summary>
        public static readonly DateTimeOffset ReferenceTime =
            new DateTimeOffset(1904, 1, 1, 0, 0, 0, TimeSpan.Zero);

        /// <summary>
        /// Converts a sequence of Harp timestamps, in seconds, into a sequence of
        /// date and time values.
        /// </summary>
        /// <param name="source">A sequence of Harp timestamps, in seconds.</param>
        /// <returns>A sequence of date and time values.</returns>
        public IObservable<DateTimeOffset> Process(IObservable<double> source)
        {
            return source.Select(seconds => ReferenceTime.AddSeconds(seconds));
        }

        /// <summary>
        /// Converts the timestamp of a sequence of Harp messages into a sequence of
        /// date and time values.
        /// </summary>
        /// <param name="source">
        /// A sequence of Harp messages. Every message must carry a timestamp.
        /// Messages sent to a device do not.
        /// </param>
        /// <returns>A sequence of date and time values.</returns>
        public IObservable<DateTimeOffset> Process(IObservable<HarpMessage> source)
        {
            return source.Select(message => ReferenceTime.AddSeconds(message.GetTimestamp()));
        }

        /// <summary>
        /// Converts the Harp timestamp of a sequence of timestamped payloads into a
        /// date and time, and keeps the value.
        /// </summary>
        /// <typeparam name="TValue">The type of the timestamped payload value.</typeparam>
        /// <param name="source">
        /// A sequence of timestamped payloads, as Parse returns for a timestamped
        /// register such as TimestampedGateState.
        /// </param>
        /// <returns>
        /// A sequence of values, each with the date and time the device reported it.
        /// This is the shape the Timestamp operator produces, so a workflow reads
        /// <c>Timestamp</c> and <c>Value</c> whichever clock it used.
        /// </returns>
        public IObservable<System.Reactive.Timestamped<TValue>> Process<TValue>(
            IObservable<Timestamped<TValue>> source)
        {
            return source.Select(payload => new System.Reactive.Timestamped<TValue>(
                payload.Value,
                ReferenceTime.AddSeconds(payload.Seconds)));
        }
    }
}
