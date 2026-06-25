# Changelog

All notable changes to this project are documented here. The format is based on
Keep a Changelog, and this project uses semantic versioning.

## [0.1.0] - 2026-06-24

### Added

- Project scaffold: documented skeletons for the live and offline paths, the
  coding standards, and the architecture docs.
- Gemini Live and Vertex AI stack configuration: settings, an example scenario
  spec, and the living knowledge map template.
- Client factory and a connection checker that verifies Gemini text, Gemini
  Live, Twilio, and Whisper against the real services.
- Twilio to Gemini Live audio bridge: a websocket server, the audio conversion
  between Twilio mulaw and Gemini PCM, and an outbound call placer.
- Commit and versioning skill that defines the rules for this repository.
