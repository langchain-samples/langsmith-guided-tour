---
name: order-summary
description: Write a clear customer-facing order status summary. Use this skill when asked to summarize an order, recap a shipment, or explain where an order is.
---

# Order Summary Skill

## Format

- **Header**: Order id and current status in plain words
- **Timeline**: Order placed → shipped → expected delivery (ETA), with the carrier and tracking number
- **Items**: Bulleted list of what's in the order
- **Next Step**: One line on what the customer can do next (track, wait, or contact support)

## Tone

- Reassuring and direct — lead with the status the customer cares about
- Use only the status, dates, and tracking returned by `get_order_status`; never estimate dates
- If the order isn't found, say so and suggest checking the order id

## Length

- Ideal: 80-150 words
- Skip sections that don't apply rather than padding them
