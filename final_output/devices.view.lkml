view: {
  devices: {
    sql_table_name: dim_device ;;
    description: "Semantic model for device analytics providing comprehensive device
    information from user sessions including device specifications, operating system details,
    and browser information for analysis and metrics.

    Based on the dim_device conforming layer model.
    "

    dimension: {
      session: {
        type: string
        sql: session_sk ;;
        description: "Session surrogate key"
        primary_key: yes
      }

      device_type: {
        type: string
        sql: device_type ;;
        description: "Type of device (mobile, desktop, tablet)"
      }

      device_manufacturer: {
        type: string
        sql: device_manufacturer ;;
        description: "Manufacturer of the device (Apple, Samsung, etc.)"
      }

      device_model: {
        type: string
        sql: device_model ;;
        description: "Specific model of the device"
      }

      device_category: {
        type: string
        sql: device_category ;;
        description: "Derived category for device type"
      }

      os_name: {
        type: string
        sql: os_name ;;
        description: "Operating system name (iOS, Android, Windows)"
      }

      os_version: {
        type: string
        sql: os_version ;;
        description: "Version of the operating system"
      }

      os_version_group: {
        type: string
        sql: os_version_group ;;
        description: "Grouped version of the operating system for analysis"
      }

      browser: {
        type: string
        sql: browser ;;
        description: "Browser name (Chrome, Safari, Firefox)"
      }

      browser_version: {
        type: string
        sql: browser_version ;;
        description: "Version of the browser"
      }

      app_name: {
        type: string
        sql: app_name ;;
        description: "Name of the application (for mobile app sessions)"
      }

      app_version: {
        type: string
        sql: app_version ;;
        description: "Version of the application"
      }

      screen_height: {
        type: string
        sql: screen_height ;;
        description: "Height of the device screen in pixels"
      }

      screen_width: {
        type: string
        sql: screen_width ;;
        description: "Width of the device screen in pixels"
      }

      screen_aspect_ratio: {
        type: string
        sql: screen_aspect_ratio ;;
        description: "Aspect ratio of the screen"
      }

      context_locale: {
        type: string
        sql: context_locale ;;
        description: "Locale setting of the device (en-US, etc.)"
      }

      context_timezone: {
        type: string
        sql: context_timezone ;;
        description: "Timezone of the device"
      }

      is_mobile_app: {
        type: string
        sql: is_mobile_app ;;
        description: "Boolean flag indicating if session is from mobile app"
      }

      is_bot: {
        type: string
        sql: is_bot ;;
        description: "Boolean flag indicating if session is from a bot"
      }
    }
  }
}