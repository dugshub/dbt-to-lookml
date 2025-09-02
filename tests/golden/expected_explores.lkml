explore: {
  rental_orders: {
    type: table
    from: rental_orders
    description: "Semantic model for rental transactions based on the fct_rental conforming
    layer.

    This model enables self-service analytics for rental revenue, volumes, and operational
    metrics.

    Provides a single source of truth for rental-related business metrics and dimensions.
    "
  }

  users: {
    type: table
    from: users
    description: "Semantic model for users based on the dim_renter conforming dimension.

    Provides comprehensive view of renter profiles, combining rental transaction behavior
    with digital engagement metrics for customer journey analysis.
    "
  }

  rental_details: {
    type: table
    from: rental_details
    description: "Semantic model for rental transaction details and attributes.

    Built on the dim_rentals conforming model to provide dimensional
    attributes for rental analysis and metric calculations.

    Primary use cases:
    - Join with rental transaction facts via rental_id
    - Segment rental analysis by payment method, source, and device
    - Filter rental metrics by rule type and guest status
    "
  }

  devices: {
    type: table
    from: devices
    description: "Semantic model for device analytics providing comprehensive device
    information from user sessions including device specifications, operating system details,
    and browser information for analysis and metrics.

    Based on the dim_device conforming layer model.
    "
  }

  sessions: {
    type: table
    from: sessions
    description: "Semantic model for user sessions providing session-level metrics and
    dimensions.

    Based on the dim_user_sessions conforming layer model.
    "
  }

  searches: {
    type: table
    from: searches
    description: "Semantic model for search analytics providing search-level metrics
    and dimensions.

    Based on the dim_searches conforming layer model.

    Enables analysis of search behavior, result quality, and conversion funnels.
    "
  }
}