view: {
  rental_orders: {
    sql_table_name: fct_rental ;;
    description: "Semantic model for rental transactions based on the fct_rental conforming
    layer.

    This model enables self-service analytics for rental revenue, volumes, and operational
    metrics.

    Provides a single source of truth for rental-related business metrics and dimensions.
    "

    dimension: {
      rental_order: {
        type: string
        sql: unique_rental_id ;;
        description: "Unique identifier for each rental transaction"
        primary_key: yes
      }

      rental_id: {
        type: string
        sql: rental_id ;;
        description: "Natural rental identifier for user reference"
      }

      facility_id: {
        type: string
        sql: facility_id ;;
        description: "Natural facility identifier for user reference"
      }

      renter_id: {
        type: string
        sql: renter_id ;;
        description: "Natural renter identifier for user reference"
      }

      reservation_status: {
        type: string
        sql: rental_reservation_status ;;
        description: "Current status of the rental reservation"
      }

      payment_status: {
        type: string
        sql: rental_payment_status ;;
        description: "Payment status of the rental"
      }

      event_type: {
        type: string
        sql: rental_event_type ;;
        description: "Type of rental event"
      }

      has_monthly_subscription: {
        type: string
        sql: case when monthly_subscription_id is not null then 'Yes' else 'No' end ;;
        description: "Whether rental is associated with monthly subscription"
      }

      has_event_booking: {
        type: string
        sql: case when event_id is not null then 'Yes' else 'No' end ;;
        description: "Whether rental is associated with an event"
      }

      has_partner_booking: {
        type: string
        sql: case when partner_id is not null then 'Yes' else 'No' end ;;
        description: "Whether rental came through a partner"
      }

      lead_time_category: {
        type: string
        sql: case
        when lead_time_days < 1 then 'Same Day'
        when lead_time_days between 1 and 7 then '1-7 Days'
        when lead_time_days between 8 and 30 then '1-4 Weeks'
        when lead_time_days > 30 then 'More than 30 Days'
        else 'Unknown'
        end ;;
        description: "Categorized lead time from booking to rental start"
      }

      duration_category: {
        type: string
        sql: case
        when rental_duration_minutes <= 60 then '1 Hour or Less'
        when rental_duration_minutes <= 240 then '2-4 Hours'
        when rental_duration_minutes <= 480 then '4-8 Hours'
        when rental_duration_minutes <= 1440 then '8-24 Hours'
        when rental_duration_minutes > 1440 then 'More than 1 Day'
        else 'Unknown'
        end ;;
        description: "Categorized rental duration"
      }
    }

    dimension_group: {
      rental_created_date: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: rental_created_date ;;
        description: "Date when the rental was created"
        label: "Created Date"
      }

      rental_starts_date: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: rental_starts_date ;;
        description: "Date when the rental period starts"
        label: "Start Date"
      }

      rental_ends_date: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: rental_ends_date ;;
        description: "Date when the rental period ends"
        label: "End Date"
      }
    }

    measure: {
      rental_count: {
        type: count
        sql: unique_rental_id ;;
        description: "Total number of rental transactions"
      }

      active_rental_count: {
        type: count
        sql: case when rental_reservation_status = 'active' then unique_rental_id else null end ;;
        description: "Count of active rental transactions"
      }

      completed_rental_count: {
        type: count
        sql: case when rental_reservation_status = 'completed' then unique_rental_id else null end ;;
        description: "Count of completed rental transactions"
      }

      canceled_rental_count: {
        type: count
        sql: case when rental_reservation_status = 'canceled' then unique_rental_id else null end ;;
        description: "Count of canceled rental transactions"
      }

      total_checkout_amount: {
        type: sum
        sql: rental_checkout_amount_local ;;
        description: "Total checkout amount across all rentals"
      }

      total_spothero_net_revenue: {
        type: sum
        sql: spothero_net_revenue_local ;;
        description: "Total SpotHero net revenue across all rentals"
      }

      total_operator_remit: {
        type: sum
        sql: operator_remit_amount_local ;;
        description: "Total amount remitted to parking operators"
      }

      total_credit_used: {
        type: sum
        sql: credit_used_amount_local ;;
        description: "Total credits used across all rentals"
      }

      avg_checkout_amount: {
        type: average
        sql: rental_checkout_amount_local ;;
        description: "Average checkout amount per rental"
      }

      avg_spothero_net_revenue: {
        type: average
        sql: spothero_net_revenue_local ;;
        description: "Average SpotHero net revenue per rental"
      }

      avg_cost_per_hour: {
        type: average
        sql: rental_cost_per_hour_local ;;
        description: "Average cost per hour of parking"
      }

      avg_spothero_revenue_per_hour: {
        type: average
        sql: spothero_net_revenue_per_hour_local ;;
        description: "Average SpotHero net revenue per hour"
      }

      avg_rental_duration_hours: {
        type: average
        sql: rental_duration_minutes / 60.0 ;;
        description: "Average rental duration in hours"
      }

      avg_lead_time_days: {
        type: average
        sql: lead_time_days ;;
        description: "Average lead time from booking to rental start in days"
      }

      min_checkout_amount: {
        type: min
        sql: rental_checkout_amount_local ;;
        description: "Minimum checkout amount"
      }

      max_checkout_amount: {
        type: max
        sql: rental_checkout_amount_local ;;
        description: "Maximum checkout amount"
      }
    }
  }
}