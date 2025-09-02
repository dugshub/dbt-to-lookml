view: {
  searches: {
    sql_table_name: dim_searches ;;
    description: "Semantic model for search analytics providing search-level metrics
    and dimensions.

    Based on the dim_searches conforming layer model.

    Enables analysis of search behavior, result quality, and conversion funnels.
    "

    dimension: {
      search: {
        type: string
        sql: search_sk ;;
        description: "Search surrogate key"
        primary_key: yes
      }

      search_id: {
        type: string
        sql: search_id ;;
        description: "Natural search identifier for user reference"
      }

      search_source: {
        type: string
        sql: search_source ;;
        description: "Source of the search (web, mobile, etc.)"
      }

      device_type: {
        type: string
        sql: device_type ;;
        description: "Device type used for search"
      }

      city: {
        type: string
        sql: city ;;
        description: "City where search was performed"
      }

      parking_type: {
        type: string
        sql: parking_type ;;
        description: "Type of parking searched for"
      }

      action_type: {
        type: string
        sql: action_type ;;
        description: "Type of search action"
      }

      is_long_search: {
        type: string
        sql: is_long_search ;;
        description: "Flag for searches lasting over 60 seconds"
      }

      is_high_engagement_search: {
        type: string
        sql: is_high_engagement_search ;;
        description: "Flag for searches with multiple actions"
      }

      has_nearby_results: {
        type: string
        sql: has_nearby_results ;;
        description: "Flag for searches with nearby results"
      }

      is_filter_applied: {
        type: string
        sql: is_filter_applied ;;
        description: "Flag for searches with filters applied"
      }
    }

    dimension_group: {
      search_date: {
        type: time
        timeframes: [
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: event_date ;;
        description: "Date when search occurred"
        label: "Search Date"
      }

      search_timestamp: {
        type: time
        timeframes: [
        time,
        hour,
        date,
        week,
        month,
        quarter,
        year,
        ]
        sql: event_timestamp ;;
        description: "Timestamp of search event"
        label: "Search Time"
      }
    }

    measure: {
      search_count: {
        type: count
        sql: search_id ;;
        description: "Total number of searches"
      }

      unique_searches: {
        type: count_distinct
        sql: search_id ;;
        description: "Count of unique searches"
      }

      unique_searching_users: {
        type: count_distinct
        sql: user_id ;;
        description: "Count of unique users who searched"
      }

      unique_searching_sessions: {
        type: count_distinct
        sql: session_id ;;
        description: "Count of unique sessions with searches"
      }

      avg_search_duration_seconds: {
        type: average
        sql: search_duration_seconds ;;
        description: "Average search duration in seconds"
      }

      total_search_actions: {
        type: sum
        sql: total_search_actions ;;
        description: "Total number of search actions"
      }

      avg_results_returned: {
        type: average
        sql: total_results_returned ;;
        description: "Average number of results returned per search"
      }

      avg_nearby_results: {
        type: average
        sql: results_under_500m ;;
        description: "Average results within 500m"
      }

      high_engagement_searches: {
        type: sum
        sql: case when is_high_engagement_search = true then 1 else 0 end ;;
        description: "Count of high engagement searches"
      }

      searches_with_filters: {
        type: sum
        sql: case when is_filter_applied = true then 1 else 0 end ;;
        description: "Count of searches with filters applied"
      }
    }
  }
}