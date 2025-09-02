view: {
  rental_details: {
    sql_table_name: dim_rentals ;;
    description: "Semantic model for rental transaction details and attributes.

    Built on the dim_rentals conforming model to provide dimensional
    attributes for rental analysis and metric calculations.

    Primary use cases:
    - Join with rental transaction facts via rental_id
    - Segment rental analysis by payment method, source, and device
    - Filter rental metrics by rule type and guest status
    "

    dimension: {
      rental: {
        type: string
        sql: rental_sk ;;
        description: "Surrogate key for rental transactions"
        primary_key: yes
      }

      rental_id: {
        type: string
        sql: rental_id ;;
        description: "Natural key for rental (for user reference/filtering)"
      }

      rental_rule_type_title: {
        type: string
        sql: rental_rule_type_title ;;
        description: "Type of pricing rule applied to the rental transaction"
      }

      payment_type_title: {
        type: string
        sql: payment_type_title ;;
        description: "Payment method used for the transaction"
      }

      rental_source_title: {
        type: string
        sql: rental_source_title ;;
        description: "Source channel through which the rental was created"
      }

      rental_source_application: {
        type: string
        sql: rental_source_application ;;
        description: "Application used to create the rental"
      }

      rental_source_device_category: {
        type: string
        sql: rental_source_device_category ;;
        description: "Device category used for the rental (mobile, desktop, tablet)"
      }

      purchased_as_guest: {
        type: string
        sql: purchased_as_guest ;;
        description: "Whether the rental was purchased without a user account"
      }
    }
  }
}