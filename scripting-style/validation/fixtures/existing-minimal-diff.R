## read the existing object ====
seu <- readRDS(file.path("derived", "upstream-object.rds"))
seu

## compare candidate settings ====
candidate_values <- c(10, 20, 30)
candidate_diagnostics <- list()

for (candidate_value in candidate_values) {
  candidate_diagnostics[[as.character(candidate_value)]] <- list(
    value = candidate_value,
    diagnostic = NA_real_
  )
}

# [决策点] Fill after inspecting candidate_diagnostics.
selected_value <- NA_real_

## continue with the selected result ====
# result <- existing_project_api(seu, selected_value)
