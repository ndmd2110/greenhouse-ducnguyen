# Builder pattern in the greenhouse project

The location configuration builder is responsible for assembling a valid `LocationConfig` before anything is written to PostgreSQL. It accepts a location name and one or more zones, validates the data, and returns an unsaved configuration object or raises `ConfigurationError`.

## Why this is Builder, not Factory Method or Abstract Factory

A Builder is the right structure here because the object we are constructing is a single configuration that is assembled step by step:

- set the location name
- add zone entries
- validate thresholds and names
- emit a complete `LocationConfig`

This is not a Factory Method because the builder does not decide which concrete type to create; it composes one complex object. It is not an Abstract Factory because we are not creating families of related product variants for multiple implementations.

## Where validation lives

Validation stays in the domain layer inside `LocationConfigBuilder` and its configuration rules. That keeps the application layer free to translate HTTP payloads and the infrastructure layer free to persist data. Invalid inputs are rejected before a database write occurs.

## Why `location_id` naming is used

The project uses the term `location` consistently for relational records and the database foreign key is named `location_id` on every zone row. This matches the business meaning of the greenhouse structure, avoids legacy `greenhouse_id` naming, and keeps API payloads and persistence consistent.

## Why assignment is not a builder method

Device assignment happens after a zone has a persisted database id. A zone does not have a stable identity until it is saved, so assignment is managed by a separate service that updates `devices.zone_id` and `devices.location_id` in the same write. This avoids rebuilding or mutating a location configuration as part of device movement.
