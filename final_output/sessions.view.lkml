view: {
  sessions: {
    sql_table_name: dim_user_sessions ;;
    description: "Semantic model for user sessions providing session-level metrics and
    dimensions.

    Based on the dim_user_sessions conforming layer model.
    "

    dimension: {
      session: {
        type: string
        sql: session_sk ;;
        description: "Session surrogate key"
        primary_key: yes
      }

      session_id: {
        type: string
        sql: session_id ;;
        description: "Natural session identifier for user reference"
      }

      platform: {
        type: string
        sql: platform ;;
        description: "Platform used for the session"
      }

      is_logged_in: {
        type: string
        sql: is_logged_in ;;
        description: "Whether user was logged in during session"
      }

      user_session_type: {
        type: string
        sql: user_session_type ;;
        description: "Type of user session"
      }

      session_length_bucket: {
        type: string
        sql: session_length_bucket ;;
        description: "Categorized session length"
      }

      marketing_channel: {
        type: string
        sql: marketing_channel ;;
        description: "Marketing channel attribution"
      }

      utm_source: {
        type: string
        sql: utm_source ;;
        description: "UTM source parameter"
      }

      utm_medium: {
        type: string
        sql: utm_medium ;;
        description: "UTM medium parameter"
      }

      utm_campaign: {
        type: string
        sql: utm_campaign ;;
        description: "UTM campaign parameter"
      }
    }

    dimension_group: {
      session_start: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: session_starts_at ;;
        description: "Session start date"
        label: "Session Start"
      }

      session_end: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: session_ends_at ;;
        description: "Session end date"
        label: "Session End"
      }

      event_date: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: event_date ;;
        description: "Date of the session event"
        label: "Event Date"
      }
    }

    measure: {
      session_count: {
        type: count
        sql: session_id ;;
        description: "Count of sessions"
      }

      unique_sessions: {
        type: count_distinct
        sql: session_id ;;
        description: "Count of unique sessions"
      }

      unique_users: {
        type: count_distinct
        sql: user_id ;;
        description: "Count of unique registered users"
      }

      unique_anonymous_users: {
        type: count_distinct
        sql: anonymous_id ;;
        description: "Count of unique anonymous users"
      }

      logged_in_sessions: {
        type: sum
        sql: case when is_logged_in = true then 1 else 0 end ;;
        description: "Count of sessions where user was logged in"
      }

      anonymous_sessions: {
        type: sum
        sql: case when user_id is null then 1 else 0 end ;;
        description: "Count of anonymous sessions"
      }

      avg_session_length_minutes: {
        type: average
        sql: session_length_minutes ;;
        description: "Average session length in minutes"
      }

      total_session_time_minutes: {
        type: sum
        sql: session_length_minutes ;;
        description: "Total session time across all sessions in minutes"
      }
    }
  }
}