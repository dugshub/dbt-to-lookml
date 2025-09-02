view: {
  users: {
    sql_table_name: dim_renter ;;
    description: "Semantic model for users based on the dim_renter conforming dimension.

    Provides comprehensive view of renter profiles, combining rental transaction behavior
    with digital engagement metrics for customer journey analysis.
    "

    dimension: {
      user: {
        type: string
        sql: renter_sk ;;
        description: "Primary user entity"
        primary_key: yes
      }

      renter_sk: {
        type: string
        sql: renter_sk ;;
        description: "Surrogate key for the renter dimension"
      }

      user_id: {
        type: string
        sql: user_id ;;
        description: "Natural key - unique identifier for the user"
      }

      email: {
        type: string
        sql: email ;;
        description: "User's email address"
      }

      first_name: {
        type: string
        sql: first_name ;;
        description: "User's first name"
      }

      last_name: {
        type: string
        sql: last_name ;;
        description: "User's last name"
      }

      mixpanel_id: {
        type: string
        sql: mixpanel_id ;;
        description: "Analytics tracking identifier"
      }

      rental_frequency_category: {
        type: string
        sql: rental_frequency_category ;;
        description: "Classification of rental frequency (rare/occasional/regular/frequent)"
      }

      renter_engagement_tier: {
        type: string
        sql: renter_engagement_tier ;;
        description: "Business classification combining rental frequency and digital engagement"
      }

      channel_preference: {
        type: string
        sql: channel_preference ;;
        description: "User's preferred interaction channel based on session data"
      }

      is_active_renter: {
        type: string
        sql: is_active_renter ;;
        description: "Flag indicating if user is currently an active renter"
      }

      is_high_value_renter: {
        type: string
        sql: is_high_value_renter ;;
        description: "Flag for high-value renters (>20 sessions and >5 rentals)"
      }
    }

    dimension_group: {
      date_joined: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: date_joined ;;
        description: "Date when user account was created"
        label: "Date Joined"
      }

      first_rental_date: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: first_rental_date ;;
        description: "Date of user's first rental"
        label: "First Rental Date"
      }

      last_rental_date: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: last_rental_date ;;
        description: "Date of user's most recent rental"
        label: "Last Rental Date"
      }

      last_activity_date: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: last_activity_date ;;
        description: "Most recent activity across all channels"
        label: "Last Activity Date"
      }
    }

    measure: {
      user_count: {
        type: count_distinct
        sql: renter_sk ;;
        description: "Total number of unique users"
      }

      total_rentals: {
        type: sum
        sql: total_rentals ;;
        description: "Total number of rentals across all users"
      }

      total_completed_rentals: {
        type: sum
        sql: total_completed_rentals ;;
        description: "Total number of completed rentals"
      }

      total_cancelled_rentals: {
        type: sum
        sql: total_cancelled_rentals ;;
        description: "Total number of cancelled rentals"
      }

      total_sessions: {
        type: sum
        sql: total_sessions ;;
        description: "Total number of digital sessions"
      }

      total_searches: {
        type: sum
        sql: total_searches ;;
        description: "Total number of search events"
      }

      avg_rentals_per_user: {
        type: average
        sql: total_rentals ;;
        description: "Average number of rentals per user"
      }

      avg_session_duration: {
        type: average
        sql: avg_session_duration ;;
        description: "Average session duration in minutes"
      }

      avg_account_age_days: {
        type: average
        sql: account_age_days ;;
        description: "Average account age in days"
      }

      avg_days_between_rentals: {
        type: average
        sql: avg_days_between_rentals ;;
        description: "Average days between rentals"
      }

      rental_completion_rate: {
        type: average
        sql: cast(total_completed_rentals as double) / nullif(total_rentals, 0) ;;
        description: "Average ratio of completed to total rentals"
      }

      search_to_rental_conversion_rate_avg: {
        type: average
        sql: search_to_rental_conversion_rate ;;
        description: "Average search to rental conversion rate"
      }
    }
  }
}