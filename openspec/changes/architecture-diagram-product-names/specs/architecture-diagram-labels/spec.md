## ADDED Requirements

### Requirement: Diagram nodes use Microsoft product names
Every node in the `docs/architecture.md` main architecture diagram SHALL display the official Microsoft product or service name (e.g., "Microsoft Forms", "Power Automate", "Azure Functions", "Azure Key Vault", "Microsoft Fabric Lakehouse", "Power BI").

#### Scenario: Reader identifies the product for each node
- **WHEN** a reader views the architecture diagram
- **THEN** every node label SHALL include a recognized Microsoft product or service name

#### Scenario: Functional role is preserved
- **WHEN** a node represents a specific role (e.g., registration intake vs data collection)
- **THEN** the label SHALL include a brief role description alongside the product name

### Requirement: Platform-level visual grouping
The diagram SHALL group nodes into subgraphs by Microsoft platform: Microsoft 365, Azure Platform, and Microsoft Fabric.

#### Scenario: M365 components grouped together
- **WHEN** a reader views the diagram
- **THEN** Microsoft Forms and Power Automate nodes SHALL appear inside a "Microsoft 365" subgraph

#### Scenario: Azure components grouped together
- **WHEN** a reader views the diagram
- **THEN** Azure Functions and Azure Storage nodes SHALL appear inside an "Azure Platform" subgraph

#### Scenario: Fabric components grouped together
- **WHEN** a reader views the diagram
- **THEN** Fabric Lakehouse and Power BI nodes SHALL appear inside a "Microsoft Fabric" subgraph

### Requirement: Supplementary visual signals
Each node SHALL include an emoji prefix as a supplementary visual signal to aid quick scanning, in addition to text labels.

#### Scenario: Emoji does not replace text
- **WHEN** a diagram node uses an emoji prefix
- **THEN** the node SHALL also include the full product name as text so meaning is conveyed without emoji rendering

### Requirement: Existing connections preserved
All data flow connections and relationships from the original diagram SHALL be preserved in the updated diagram.

#### Scenario: Connection count unchanged
- **WHEN** comparing the updated diagram to the original
- **THEN** all original edge connections between nodes SHALL still exist
