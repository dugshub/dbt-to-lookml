include: "rental_orders.view.lkml"
include: "users.view.lkml"
include: "searches.view.lkml"

explore: rental_orders {
  from: rental_orders
  description: "Rental transaction fact table"

  join: users {
    sql_on: ${rental_orders.user_sk} = ${users.user_sk} ;;
    relationship: many_to_one
    type: left_outer
    fields: [users.dimensions_only*]
  }

  join: searches {
    sql_on: ${rental_orders.search_sk} = ${searches.search_sk} ;;
    relationship: many_to_one
    type: left_outer
    fields: [searches.dimensions_only*]
  }
}

explore: users {
  from: users
  description: "User dimension table with renter profile data"
}

explore: searches {
  from: searches
  description: "Search dimension table for search analytics"

  join: users {
    sql_on: ${searches.user_sk} = ${users.user_sk} ;;
    relationship: many_to_one
    type: left_outer
    fields: [users.dimensions_only*]
  }
}