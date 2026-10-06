#############################################################
las_info <- function(in_las_folder, rprocesses)
{
    library(lidR)
    library(future)
    library(sf)
    library(units)

    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    print("Loading LiDAR data...")

    ctg <- readLAScatalog(
        in_las_folder,
        filter = "-drop_class 7"
    )

    print(
        paste0(
            "Data format: v",
            ctg@data$Version.Major[1],
            ".",
            ctg@data$Version.Minor[1]
        )
    )

    # CRS information
    crs_info <- sf::st_crs(ctg)

    if (is.null(crs_info) || is.na(crs_info$wkt))
    {
        print("CRS: Unknown")
    }
    else
    {
        if (!is.na(crs_info$epsg))
        {
            print(paste0("EPSG: ", crs_info$epsg))
        }

        if (!is.null(crs_info$Name))
        {
            print(paste0("CRS: ", crs_info$Name))
        }

        if (!is.null(crs_info$ud_unit))
        {
            print(
                paste0(
                    "Units: ",
                    units::deparse_unit(crs_info$ud_unit)
                )
            )
        }
    }

    print(
        paste0(
            "Extent: ",
            round(min(ctg@data$Min.X), 2), " ",
            round(max(ctg@data$Max.X), 2), " ",
            round(min(ctg@data$Min.Y), 2), " ",
            round(max(ctg@data$Max.Y), 2)
        )
    )

    area_m2 <- as.numeric(st_area(ctg))

    print(
        paste0(
            "Area: ",
            round(area_m2 / 1000000, 2),
            " km²"
        )
    )

    total_pts <- sum(ctg@data$Number.of.point.records)

    print(
        paste0(
            "Total Points: ",
            format(total_pts, big.mark = ",")
        )
    )

    print(
        paste0(
            "Density: ",
            round(total_pts / area_m2, 2),
            " pts/m²"
        )
    )

    print(
        paste0(
            "Total Files: ",
            length(ctg@data$filename)
        )
    )

    # Normalization check
    las <- readLAS(ctg@data$filename[1])

    ground <- filter_poi(
        las,
        Classification == 2
    )

    if (!is.empty(ground))
    {
        mean_ground_z <- mean(abs(ground$Z), na.rm = TRUE)

        print(
            paste0(
                "Normalized: ",
                ifelse(mean_ground_z < 1, "YES", "NO")
            )
        )

        print(
            paste0(
                "Ground Z Range: ",
                round(min(ground$Z), 2),
                " to ",
                round(max(ground$Z), 2)
            )
        )
    }
    else
    {
        print(
            "Normalized: Unknown (no class 2 ground points found)"
        )
    }

    print(
        paste0(
            "Z Range: ",
            round(min(las$Z), 2),
            " to ",
            round(max(las$Z), 2)
        )
    )

    plan(sequential)
}
#########################################################################################
dtm_by_tin <- function(in_las_folder, out_folder, cell_size, rprocesses) {

    library(lidR)
    library(terra)
    library(future)
    library(tools)

    if (cell_size < 1.0) { rprocesses = rprocesses / 2 }
    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    ctg <- readLAScatalog(in_las_folder, filter = '-drop_class 7')
    print("Generate DTM...")
    opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/{*}_TIN_DTM")
    ctg@output_options$
      drivers$
      SpatRaster$
      param$
      overwrite <- TRUE
    #         ctg@output_options$drivers$Raster$param$overwrite <- TRUE
    opt_progress(ctg) <- TRUE
    dtm <- rasterize_terrain(ctg, res = cell_size, algorithm = tin())

    mosaic_catalog_outputs(ctg,out_folder,"_TIN_DTM.tif","Merged_TIN_DTM.tif")

    # reset R mutilsession back to default
    plan(sequential)
}

#########################################################################################
dtm_by_knnidw <- function(in_las_folder, out_folder, cell_size, rprocesses) {

    library(lidR)
    library(terra)
    library(future)
    library(tools)

    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    ctg <- readLAScatalog(in_las_folder, filter = '-drop_class 7')
    print("Generate DTM...")
    opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/{*}_IDW_DTM")
    ctg@output_options$
      drivers$
      SpatRaster$
      param$
      overwrite <- TRUE
    ctg@output_options$drivers$Raster$param$overwrite <- TRUE
    opt_progress(ctg) <- TRUE
    dtm <- rasterize_terrain(ctg, res = cell_size, algorithm = knnidw())

    mosaic_catalog_outputs(ctg,out_folder,"_IDW_DTM.tif","Merged_IDW_DTM.tif")

    # reset R mutilsession back to default
    plan(sequential)
}

#########################################################################################
dtm_by_kriging <- function(in_las_folder, out_folder, cell_size, rprocesses) {

    library(lidR)
    library(terra)
    library(future)
    library(tools)
    if (cell_size < 1.0) { rprocesses = rprocesses / 2 }
    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    ctg <- lidR::readLAScatalog(in_las_folder, filter = '-drop_class 7')
    print("Generate DTM...")
    opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/{*}_K_DTM")
    ctg@output_options$
      drivers$
      SpatRaster$
      param$
      overwrite <- TRUE
    ctg@output_options$drivers$Raster$param$overwrite <- TRUE
    opt_progress(ctg) <- TRUE
    dtm <- lidR::rasterize_terrain(ctg, res = cell_size, algorithm = kriging())

    mosaic_catalog_outputs(ctg,out_folder,"_K_DTM.tif","Merged_K_DTM.tif")

    print("Generate DTM...Done")
    # reset R mutilsession back to default
    plan(sequential)


}

#########################################################################################
pd2cellsize <- function(in_las_folder, rprocesses)
{
    library(lidR)
    library(future)
    library(sf)
    library(units)

    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    print(
        "Calculate output's raster average cell size from point density..."
    )

    if (
        lidR::is(in_las_folder, "LAS") ||
        lidR::is(in_las_folder, "LAScatalog")
    )
    {
        ctg <- in_las_folder
    }
    else
    {
        ctg <- lidR::readLAScatalog(
            in_las_folder,
            filter = "-drop_class 7"
        )
    }

    crs_info <- sf::st_crs(ctg)

    map_units <- "Unknown"

    if (!is.null(crs_info$ud_unit))
    {
        map_units <- units::deparse_unit(crs_info$ud_unit)
    }

    point_density <-
        sum(ctg@data$Number.of.point.records) /
        lidR::st_area(ctg)

    mean_pd <- sqrt(3 / point_density)

    cell_size <- round(
        0.05 * round(mean_pd / 0.05),
        2
    )

    print(
        paste0(
            "Calculated cell size: ",
            cell_size,
            " ",
            map_units
        )
    )

    plan(sequential)

    return(
        list(
            cell_size = cell_size,
            map_units = map_units,
            point_density = point_density
        )
    )
}

#########################################################################################
chm_by_dsmtin <- function(in_las_folder, out_folder, cell_size, is_normalized, rprocesses) {
    library(lidR)
    library(terra)
    library(future)
    library(tools)

    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    ctg <- readLAScatalog(in_las_folder, filter = '-drop_class 7')
    if (is_normalized) {
        print("Generating CHM using TIN...")
        opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/{*}_TIN_CHM") }
    else {
        print("Generating DSM using TIN...")
        opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/{*}_TIN_DSM") }

    ctg@output_options$
      drivers$
      SpatRaster$
      param$
      overwrite <- TRUE
    ctg@output_options$drivers$Raster$param$overwrite <- TRUE
    opt_progress(ctg) <- TRUE
    chm <- lidR::rasterize_canopy(ctg, cell_size, dsmtin(max_edge = (3 * cell_size)), pkg = "terra")

     if (is_normalized) {
        mosaic_catalog_outputs(ctg,out_folder,"_TIN_CHM.tif","Merged_TIN_CHM.tif")}
    else {
        mosaic_catalog_outputs(ctg,out_folder,"_TIN_DSM.tif","Merged_TIN_DSM.tif")}

    # reset R mutilsession back to default
    plan(sequential)
}

#########################################################################################
chm_by_pitfree <- function(in_las_folder, out_folder, cell_size, is_normalized, rprocesses) {

    library(lidR)
    library(terra)
    library(future)
    library(tools)

    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    ctg <- readLAScatalog(in_las_folder, filter = '-drop_class 7 -drop_overlap')

    if (is_normalized) {
        print("Generate CHM using Pit-free...")
        opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/{*}_PitF_CHM") }
    else {
        print("Generate DSM using Pit-free...")
        opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/{*}_PitF_DSM") }

    ctg@output_options$
      drivers$
      SpatRaster$
      param$
      overwrite <- TRUE
    ctg@output_options$drivers$Raster$param$overwrite <- TRUE
    opt_progress(ctg) <- TRUE
    chm <- rasterize_canopy(ctg, cell_size, pitfree(thresholds = c(0, 3, 5, 10, 15, 20), max_edge = c(0, 3 * cell_size), subcircle = (cell_size)))

     if (is_normalized) {
        mosaic_catalog_outputs(ctg,out_folder,"_PitF_CHM.tif","Merged_PitF_CHM.tif")}
    else {
        mosaic_catalog_outputs(ctg,out_folder,"_PitF_DSM.tif","Merged_PitF_DSM.tif")}
   # reset R mutilsession back to default
    plan(sequential)

}

#########################################################################################
detect_normalized <- function(in_las_folder)
{  library(lidR)

    las <- readLAS(
        list.files(
            in_las_folder,
            pattern = "\\.la(s|z)$",
            full.names = TRUE
        )[1]
    )

    ground <- filter_poi(
        las,
        Classification == 2
    )

    if (is.empty(ground))
    {
        return(FALSE)
    }

    mean_ground_z <- mean(
        abs(ground$Z),
        na.rm = TRUE
    )

    return(mean_ground_z < 1)
}
#############################################################
mosaic_catalog_outputs <- function(
    ctg,
    out_folder,
    suffix,
    merged_name
)
{
    files <- file.path(
        out_folder,
        paste0(
            tools::file_path_sans_ext(
                basename(ctg@data$filename)
            ),
            suffix
        )
    )

    files <- files[file.exists(files)]

    print(files)

    if (length(files) > 1)
    {
        rast_list <- lapply(
            files,
            terra::rast
        )

        terra::mosaic(
            terra::sprc(rast_list),
            fun = "first",
            filename = file.path(
                out_folder,
                merged_name
            ),
            overwrite = TRUE
        )

        print(
            paste0(
                "Created merged raster: ",
                merged_name
            )
        )
    }
}
################################################################################################
hh_function <- function(in_las_folder,out_folder, cell_size, Smooth_by, Min_ws, lawn_range, rprocesses) {

    library(lidR)
    library(terra)
    library(sf)
    library(future)

    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    print('Generating Hummock/ Hollow Raster ...')
    ctg <- readLAScatalog(in_las_folder, select = 'xyzc', filter = '-drop_class 7')

    HH_raster <- function(chunk, radius, cell_size, lawn_range, Smooth_by)
    {
        if (inherits(chunk, "LAS")) {
            las <- chunk
        } else {
                las <- readLAS(chunk)}
        if (is.empty(las)) return(NULL)

        las_1 <- filter_poi(las, buffer == 0)
        hull <- st_convex_hull(las_1)

        # convert to SpatialPolygons
        bbox <- vect(hull)

        #las to DTM
        dtm <- rasterize_terrain(las, res = cell_size, algorithm = tin())

        gfw <- focalMat(dtm, radius, "circle")
        gfw[gfw > 0] = 1
        gfw[gfw == 0] = NA
        sdtm <- focal(dtm, w = gfw, fun = Smooth_by, na.policy = "omit", na.rm = TRUE, fillvalue = NA, expand = TRUE)
        ndtm <- (sdtm - dtm)
        positive <- abs(lawn_range)
        negative <- positive * -1

        HH <- ifel(ndtm < negative, 1, ifel(ndtm > positive, -1, 0))

        cont_hh <- (crop(ndtm, ext(bbox))) * -1
        hh <- crop(HH, ext(bbox))

        return(list(cont_hh, hh, radius, Smooth_by))
    }

    MultiWrite = function(output_list, file) {
        chh = output_list[[1]]
        hh = output_list[[2]]
        radius = output_list[[3]]
        Smooth_by = output_list[[4]]
        base_name <- basename(file)
        path1 <- file.path(dirname(file),paste0("CHH_", base_name, ".tif"))
        path2 <- file.path(dirname(file),paste0("HH_", base_name, ".tif"))
        terra::writeRaster(chh, path1, overwrite = TRUE)
        terra::writeRaster(hh, path2, overwrite = TRUE)
    }

    MultiWriteDriver = list(
      write = MultiWrite,
      extension = "",
      object = "output_list",
      path = "file",
      param = list())

    ctg@output_options$drivers$list <- MultiWriteDriver

    opt_chunk_alignment(ctg) <- c(0, 0)
    opt_output_files(ctg) <- paste0(out_folder, "/{*}_", Smooth_by, "_", Min_ws, "m")
    ctg@output_options$
      drivers$
      SpatRaster$
      param$
      overwrite <- TRUE
    opt_stop_early(ctg) <- TRUE
    # Min_ws is the diameter of the circular moving window; focalMat() takes its radius
    out <- catalog_apply(ctg, HH_raster, radius = Min_ws / 2, cell_size = cell_size, lawn_range = lawn_range, Smooth_by = Smooth_by)
    chh_files <- list.files(
        out_folder,
        pattern = "^CHH_.*\\.tif$",
        full.names = TRUE
    )

    hh_files <- list.files(
        out_folder,
        pattern = "^HH_.*\\.tif$",
        full.names = TRUE
    )

    chhs <- terra::sprc(chh_files)
    hhs  <- terra::sprc(hh_files)

    terra::writeRaster(
        terra::mosaic(chhs),
        file.path(out_folder,
                  paste0("Merged_CHH_", Smooth_by, "_", Min_ws, "m.tif")),
        overwrite = TRUE
    )

    terra::writeRaster(
        terra::mosaic(hhs),
        file.path(out_folder,
                  paste0("Merged_HH_", Smooth_by, "_", Min_ws, "m.tif")),
        overwrite = TRUE
    )

    # reset R mutilsession back to default
    plan(sequential)

}

###########################################################################

classify_gnd_csf <- function(in_las_folder, out_folder, slope, class_threshold, cloth_resolution, rigidness,rprocesses,rest) {
    library(lidR)
    library(future)
    library(RCSF)

    print("loading LiDAR Data")
    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    ctg <- readLAScatalog(in_las_folder, filter = '-drop_class 7 -drop_overlap')
    opt_output_files(ctg) <- paste0(out_folder, "/{*}_gnd_classified")
    opt_laz_compression(ctg) <- FALSE
    gnd_csf <- csf(slope, class_threshold = class_threshold, cloth_resolution = cloth_resolution, rigidness = rigidness, iterations = 500, time_step = 0.65)
    print("Classify ground start....")
    if (rest == TRUE) {suppressMessages({
    c_ctg <- classify_ground(ctg, gnd_csf)})
    }
    else{c_ctg <- classify_ground(ctg, gnd_csf)}
}
############################################################################################
detect_ground_classified <- function(in_las_folder)
{
    library(lidR)

    las <- readLAS(
        list.files(
            in_las_folder,
            pattern = "\\.la(s|z)$",
            full.names = TRUE
        )[1]
    )

    any(las$Classification == 2)
}
############################################################################################
# Seismic line disturbance analysis
# Adapted from the analysis script of Chan, Dabros & McDermid (2026), "Microtopographic and
# Hydrological Response to Repeated Seismic Line Disturbance in a Boreal Fen of Northern
# Alberta, Canada", Forests 17, 489. Compares elevation, hummock cover, depth-to-water and
# surface water on seismic line segments against the adjacent matrix segments, by
# disturbance class. Uses only terra and ggplot2; the statistical tests are base R.
############################################################################################

# Brown-Forsythe test for equality of group means under unequal variances.
# Same statistic as onewaytests::bf.test, which the published analysis script uses.
bf_means_test <- function(y, g) {
    ok <- !is.na(y) & !is.na(g)
    y <- y[ok]
    g <- droplevels(as.factor(g[ok]))
    n <- tapply(y, g, length)
    m <- tapply(y, g, mean)
    v <- tapply(y, g, var)
    N <- sum(n)
    w <- (1 - n / N) * v
    stat <- sum(n * (m - sum(n * m) / N)^2) / sum(w)
    df1 <- nlevels(g) - 1
    df2 <- 1 / sum((w / sum(w))^2 / (n - 1))
    list(statistic = unname(stat), df1 = df1, df2 = unname(df2),
         p.value = unname(pf(stat, df1, df2, lower.tail = FALSE)))
}

# Pairwise tests between all class pairs, BH-adjusted. test_fun(y, g) returns a p-value.
pairwise_p <- function(y, g, test_fun) {
    pairs <- t(combn(levels(g), 2))
    p <- apply(pairs, 1, function(pr) {
        idx <- g %in% pr
        test_fun(y[idx], droplevels(g[idx]))
    })
    data.frame(group1 = pairs[, 1], group2 = pairs[, 2], p_value = p,
               p_adjusted = p.adjust(p, method = "BH"), stringsAsFactors = FALSE)
}

# Compact letter display: groups sharing a letter do not differ significantly.
# Insert-absorb algorithm; letters are assigned in class order.
group_letters <- function(levs, pairs, alpha, uppercase = TRUE) {
    cols <- list(levs)
    sig <- pairs[!is.na(pairs$p_adjusted) & pairs$p_adjusted < alpha, , drop = FALSE]
    for (k in seq_len(nrow(sig))) {
        a <- sig$group1[k]
        b <- sig$group2[k]
        split_cols <- list()
        for (col in cols) {
            if (a %in% col && b %in% col) {
                split_cols <- c(split_cols, list(setdiff(col, a)), list(setdiff(col, b)))
            } else {
                split_cols <- c(split_cols, list(col))
            }
        }
        # Absorb columns contained in another column (or repeating an earlier one)
        keep <- vapply(seq_along(split_cols), function(i) {
            !any(vapply(seq_along(split_cols), function(j) {
                j != i && all(split_cols[[i]] %in% split_cols[[j]]) &&
                    (length(split_cols[[j]]) > length(split_cols[[i]]) || j < i)
            }, logical(1)))
        }, logical(1))
        cols <- split_cols[keep]
    }
    cols <- cols[order(vapply(cols, function(col) min(match(col, levs)), numeric(1)))]
    abc <- (if (uppercase) LETTERS else letters)[seq_along(cols)]
    vapply(levs, function(lv) {
        paste(abc[vapply(cols, function(col) lv %in% col, logical(1))], collapse = "")
    }, character(1))
}

seismic_line_analysis <- function(segments_path, segments_layer, dtm_path, microform_path,
                                  dtw_path, out_folder, alpha) {
    library(terra)
    library(ggplot2)

    tables_dir <- file.path(out_folder, "tables")
    plots_dir <- file.path(out_folder, "plots")
    dir.create(tables_dir, showWarnings = FALSE, recursive = TRUE)
    dir.create(plots_dir, showWarnings = FALSE, recursive = TRUE)

    print("Reading input data...")
    segs <- if (nzchar(segments_layer)) vect(segments_path, layer = segments_layer) else vect(segments_path)
    missing_fields <- setdiff(c("new_id", "note", "Class"), names(segs))
    if (length(missing_fields) > 0) {
        stop("Segment layer is missing field(s): ", paste(missing_fields, collapse = ", "),
             ". Expected new_id, note ('original' or 'matrix') and Class.")
    }
    bad_notes <- setdiff(unique(segs$note), c("original", "matrix"))
    if (length(bad_notes) > 0) {
        stop("Field 'note' must be 'original' (seismic line) or 'matrix'; found: ",
             paste(bad_notes, collapse = ", "))
    }

    dtm <- rast(dtm_path)
    microform <- rast(microform_path)
    has_dtw <- nzchar(dtw_path)
    dtw <- if (has_dtw) rast(dtw_path) else NULL
    if (!same.crs(segs, dtm)) {
        print("Projecting segments to the DTM's coordinate system...")
        segs <- project(segs, dtm)
    }

    # Class order and colours: the paper's three classes keep its order and palette
    known_colours <- c("New Disturbance" = "#A3FF73", "Old Disturbance" = "#F64A7D",
                       "Re-disturbance" = "#E79800")
    line_classes <- unique(segs$Class[segs$note == "original"])
    line_classes <- line_classes[!is.na(line_classes)]
    class_levels <- if (all(line_classes %in% names(known_colours))) {
        names(known_colours)[names(known_colours) %in% line_classes]
    } else {
        sort(line_classes)
    }
    if (length(class_levels) < 2) stop("At least two disturbance classes are needed in field 'Class'.")
    class_colours <- setNames(grDevices::hcl.colors(length(class_levels), "Dark 3"), class_levels)
    known <- intersect(class_levels, names(known_colours))
    class_colours[known] <- known_colours[known]

    # ---- Per-segment values (one terra::extract per raster) --------------------------------
    print(paste("Extracting raster values over", nrow(segs), "segments..."))
    seg_values <- function(r) {
        v <- terra::extract(r, segs)
        split(v[[2]], factor(v$ID, levels = seq_len(nrow(segs))))
    }
    seg_df <- data.frame(new_id = segs$new_id, note = segs$note, Class = segs$Class,
                         stringsAsFactors = FALSE)

    vals <- seg_values(dtm)
    seg_df$dtm_mean <- vapply(vals, mean, numeric(1), na.rm = TRUE)
    seg_df$dtm_median <- vapply(vals, median, numeric(1), na.rm = TRUE)
    seg_df$dtm_sd <- vapply(vals, sd, numeric(1), na.rm = TRUE)

    mf_vals <- seg_values(microform)
    count <- function(v, code) sum(v == code, na.rm = TRUE)
    n_hum <- vapply(mf_vals, count, numeric(1), code = 1)
    n_lawn <- vapply(mf_vals, count, numeric(1), code = 0)
    n_hol <- vapply(mf_vals, count, numeric(1), code = -1)
    n_cls <- n_hum + n_lawn + n_hol
    seg_df$hummock_prop <- n_hum / n_cls
    seg_df$lawn_prop <- n_lawn / n_cls
    seg_df$hollow_prop <- n_hol / n_cls

    if (has_dtw) {
        dtw_vals <- seg_values(dtw)
        # DTW is summarised over ground cells only; DTW == 0 marks surface water
        seg_df$dtw_mean <- vapply(dtw_vals, function(v) mean(v[v != 0], na.rm = TRUE), numeric(1))
        seg_df$dtw_median <- vapply(dtw_vals, function(v) median(v[v != 0], na.rm = TRUE), numeric(1))
        seg_df$water_prop <- vapply(dtw_vals, function(v) sum(v == 0, na.rm = TRUE) / length(v), numeric(1))
    }
    write.csv(seg_df, file.path(tables_dir, "segment_values.csv"), row.names = FALSE)

    # ---- Line-vs-matrix deviations ---------------------------------------------------------
    print("Computing line-vs-matrix deviations...")
    line_df <- seg_df[seg_df$note == "original" & !is.na(seg_df$Class), ]
    matrix_df <- seg_df[seg_df$note == "matrix", ]
    deviation <- function(col) {
        matrix_mean <- tapply(matrix_df[[col]], matrix_df$new_id, mean, na.rm = TRUE)
        line_df[[col]] - unname(matrix_mean[as.character(line_df$new_id)])
    }

    metrics <- list(
        dtm = list(col = "dtm_mean", ylab = bquote(Elev[Line] - Elev[Matrix] ~ "(m)")),
        hummock = list(col = "hummock_prop", ylab = bquote(Hum_Prop[Line] - Hum_Prop[Matrix]))
    )
    if (has_dtw) {
        metrics$dtw <- list(col = "dtw_mean", ylab = bquote(DTW[Line] - DTW[Matrix] ~ "(m)"))
        metrics$surfacewater <- list(col = "water_prop", ylab = bquote(SW_Prop[Line] - SW_Prop[Matrix]))
    }

    dev_df <- line_df[, c("new_id", "Class")]
    for (m in names(metrics)) dev_df[[paste0(m, "_deviation")]] <- deviation(metrics[[m]]$col)
    write.csv(dev_df, file.path(tables_dir, "segment_deviations.csv"), row.names = FALSE)

    violin_theme <- theme(
        axis.text.x = element_text(angle = 45, vjust = 1, hjust = 1, colour = "black"),
        axis.text.y = element_text(colour = "black"),
        legend.position = "none",
        panel.background = element_rect(fill = "gray99", colour = "black"),
        panel.grid.major = element_line(linewidth = 0.1, colour = "gray70"),
        panel.grid.minor = element_blank())

    # ---- Summaries, tests and violin plots per metric --------------------------------------
    print("Running statistical tests...")
    for (m in names(metrics)) {
        y <- dev_df[[paste0(m, "_deviation")]]
        ok <- is.finite(y)
        y <- y[ok]
        g <- factor(dev_df$Class[ok], levels = class_levels)

        kw <- kruskal.test(y, g)
        wilcox_pairs <- pairwise_p(y, g, function(yy, gg) {
            suppressWarnings(wilcox.test(yy ~ gg)$p.value)
        })
        bf <- bf_means_test(y, g)
        bf_pairs <- pairwise_p(y, g, function(yy, gg) bf_means_test(yy, gg)$p.value)

        mean_groups <- group_letters(class_levels, wilcox_pairs, alpha, uppercase = TRUE)
        bf_groups <- group_letters(class_levels, bf_pairs, alpha, uppercase = FALSE)

        summary_df <- do.call(rbind, lapply(class_levels, function(cl) {
            v <- y[g == cl]
            data.frame(Class = cl, n = length(v), mean = mean(v), median = median(v),
                       min = min(v), max = max(v),
                       q25 = unname(quantile(v, 0.25)), q75 = unname(quantile(v, 0.75)),
                       sd = sd(v), var = var(v),
                       mean_group = mean_groups[[cl]], bf_group = bf_groups[[cl]],
                       stringsAsFactors = FALSE)
        }))
        summary_df <- cbind(attribute = m, summary_df)
        write.csv(summary_df, file.path(tables_dir, paste0(m, "_deviation_summary.csv")), row.names = FALSE)

        write.csv(cbind(attribute = m, KW_stat = unname(kw$statistic), KW_df = unname(kw$parameter),
                        KW_pval = kw$p.value,
                        setNames(wilcox_pairs, c("Wilcoxon_group1", "Wilcoxon_group2",
                                                 "Wilcoxon_pval", "Wilcoxon_pval_adj"))),
                  file.path(tables_dir, paste0(m, "_kruskal_wilcoxon.csv")), row.names = FALSE)
        write.csv(cbind(attribute = m, BF_stat = bf$statistic, BF_df1 = bf$df1, BF_df2 = bf$df2,
                        BF_pval = bf$p.value,
                        setNames(bf_pairs, c("BF_group1", "BF_group2", "BF_pval", "BF_pval_adj"))),
                  file.path(tables_dir, paste0(m, "_brown_forsythe.csv")), row.names = FALSE)

        print(paste0(m, " deviation by class:"))
        print(summary_df[, c("Class", "n", "mean", "sd", "mean_group", "bf_group")], row.names = FALSE)

        plot_df <- data.frame(Class = g, value = y)
        label_df <- data.frame(Class = factor(class_levels, levels = class_levels),
                               value = max(y) + 0.08 * diff(range(y)),
                               label = unname(mean_groups))
        violin <- ggplot(plot_df, aes(x = Class, y = value, fill = Class)) +
            geom_violin() +
            stat_summary(fun = mean, geom = "point", size = 2) +
            geom_text(data = label_df, aes(label = label), fontface = "bold", size = 4) +
            ylab(metrics[[m]]$ylab) +
            xlab("Disturbance Class") +
            scale_fill_manual(values = class_colours) +
            violin_theme
        ggsave(file.path(plots_dir, paste0(m, "_violin.png")), violin,
               width = 3.2, height = 4, scale = 0.8, bg = "white")
    }

    # ---- Class-level proportions and stacked bar plots -------------------------------------
    print("Creating class proportion plots...")
    bar_theme <- theme(
        axis.text.x = element_text(angle = 45, vjust = 1, hjust = 1, colour = "black"),
        axis.text.y = element_text(colour = "black"),
        panel.background = element_rect(fill = "gray99", colour = "black"),
        panel.grid.major = element_blank(),
        panel.grid.minor = element_blank())

    group_label <- ifelse(seg_df$note == "matrix", "Matrix", seg_df$Class)
    bar_levels <- c("Matrix", class_levels)

    # Cell-level proportions per class, pooled over its segments
    class_cells <- function(vals_list, cl) unlist(vals_list[which(group_label == cl)])
    mf_props <- do.call(rbind, lapply(bar_levels, function(cl) {
        v <- class_cells(mf_vals, cl)
        n <- length(v)
        data.frame(Class = cl, Hummock = sum(v == 1, na.rm = TRUE) / n,
                   Lawn = sum(v == 0, na.rm = TRUE) / n, Hollow = sum(v == -1, na.rm = TRUE) / n)
    }))
    write.csv(mf_props, file.path(tables_dir, "class_microform_proportions.csv"), row.names = FALSE)

    mf_long <- data.frame(
        Class = factor(rep(mf_props$Class, 3), levels = bar_levels),
        Microform = factor(rep(c("Hummock", "Lawn", "Hollow"), each = nrow(mf_props)),
                           levels = c("Hummock", "Lawn", "Hollow")),
        proportion = c(mf_props$Hummock, mf_props$Lawn, mf_props$Hollow))
    mf_bar <- ggplot(mf_long, aes(x = Class, y = proportion, fill = Microform)) +
        geom_col(width = 0.7) +
        geom_text(aes(label = round(proportion, 2), colour = Microform),
                  position = position_stack(vjust = 0.5), size = 3, fontface = "bold",
                  show.legend = FALSE) +
        scale_fill_manual(values = c(Hummock = "#FFE924", Lawn = "#21918D", Hollow = "#440054")) +
        scale_colour_manual(values = c(Hummock = "black", Lawn = "white", Hollow = "white")) +
        ylab("Proportion") + xlab("Disturbance Class") + bar_theme
    ggsave(file.path(plots_dir, "microform_barplot.png"), mf_bar,
           width = 4.5, height = 4, scale = 0.8, bg = "white")

    if (has_dtw) {
        sw_props <- do.call(rbind, lapply(bar_levels, function(cl) {
            v <- class_cells(dtw_vals, cl)
            water <- sum(v == 0, na.rm = TRUE) / length(v)
            data.frame(Class = cl, Water = water, NonWater = 1 - water)
        }))
        write.csv(sw_props, file.path(tables_dir, "class_surfacewater_proportions.csv"), row.names = FALSE)

        sw_long <- data.frame(
            Class = factor(rep(sw_props$Class, 2), levels = bar_levels),
            Cover = factor(rep(c("Non-Water", "Water"), each = nrow(sw_props)),
                           levels = c("Non-Water", "Water")),
            proportion = c(sw_props$NonWater, sw_props$Water))
        sw_bar <- ggplot(sw_long, aes(x = Class, y = proportion, fill = Cover)) +
            geom_col(width = 0.7) +
            geom_text(aes(label = round(proportion, 2)), position = position_stack(vjust = 0.5),
                      size = 3, fontface = "bold") +
            scale_fill_manual(values = c("Non-Water" = "grey77", Water = "cornflowerblue"),
                              name = "Cover Type") +
            ylab("Proportion") + xlab("Disturbance Class") + bar_theme
        ggsave(file.path(plots_dir, "surfacewater_barplot.png"), sw_bar,
               width = 4.5, height = 4, scale = 0.8, bg = "white")
    }

    print(paste("Tables saved to:", tables_dir))
    print(paste("Plots saved to:", plots_dir))
}

############################################################################################
# Surface water mapping
# Follows the surface water classification of Chan, Dabros & McDermid (2026), Forests 17, 489
# (section 2.4): random training points in labelled polygons, an rpart decision tree on the
# orthomosaic's RGB values, a canopy height mask, and removal of small water patches.
############################################################################################
surface_water_map <- function(ortho_path, training_path, training_layer, chm_path,
                              max_canopy_height, min_patch_area, points_per_polygon, seed,
                              out_folder) {
    library(terra)
    library(rpart)

    dir.create(out_folder, showWarnings = FALSE, recursive = TRUE)

    print("Reading input data...")
    ortho <- rast(ortho_path)
    if (nlyr(ortho) < 3) stop("The orthomosaic needs at least three bands (red, green, blue).")
    ortho <- ortho[[1:3]]
    names(ortho) <- c("red", "green", "blue")

    train <- if (nzchar(training_layer)) vect(training_path, layer = training_layer) else vect(training_path)
    if (!"class" %in% names(train)) {
        stop("Training polygons need a 'class' field, with 'water' for surface water polygons.")
    }
    train$class <- tolower(trimws(train$class))
    if (!"water" %in% train$class) stop("No training polygons have class 'water'.")
    if (length(unique(train$class)) < 2) stop("Training polygons need at least one class besides 'water'.")
    if (!same.crs(train, ortho)) train <- project(train, ortho)

    # ---- Training points: random points inside each polygon --------------------------------
    set.seed(seed)
    pts <- do.call(rbind, lapply(seq_len(nrow(train)), function(i) {
        p <- spatSample(train[i], points_per_polygon, method = "random")
        values(p) <- data.frame(class = rep(train$class[i], nrow(p)))
        p
    }))
    rgb_vals <- terra::extract(ortho, pts, ID = FALSE)
    samples <- data.frame(class = factor(pts$class), rgb_vals)
    samples <- samples[complete.cases(samples), ]
    print(paste("Training points per class:",
                paste(names(table(samples$class)), table(samples$class), sep = " = ", collapse = ", ")))

    # ---- Decision tree and 5-fold cross-validation ------------------------------------------
    model <- rpart(class ~ red + green + blue, data = samples, method = "class")
    if (nrow(model$frame) == 1) {
        print(paste0("Warning! The decision tree has no splits, so every cell gets the same class. ",
                     "Add training polygons or raise points_per_polygon (rpart needs at least ",
                     "20 points to split)."))
    }

    folds <- sample(rep(1:5, length.out = nrow(samples)))
    cv_pred <- factor(rep(NA, nrow(samples)), levels = levels(samples$class))
    for (k in 1:5) {
        fold_model <- rpart(class ~ red + green + blue, data = samples[folds != k, ], method = "class")
        cv_pred[folds == k] <- predict(fold_model, samples[folds == k, ], type = "class")
    }
    accuracy <- mean(cv_pred == samples$class)
    print(paste0("5-fold cross-validation overall accuracy: ", round(100 * accuracy, 1), "%"))

    confusion <- as.data.frame.matrix(table(observed = samples$class, predicted = cv_pred))
    write.csv(cbind(observed = rownames(confusion), confusion),
              file.path(out_folder, "cv_confusion_matrix.csv"), row.names = FALSE)
    write.csv(data.frame(n_points = nrow(samples), cv_overall_accuracy = accuracy),
              file.path(out_folder, "cv_accuracy.csv"), row.names = FALSE)
    writeVector(pts, file.path(out_folder, "training_points.gpkg"), overwrite = TRUE)
    capture.output(print(model), file = file.path(out_folder, "decision_tree.txt"))

    # ---- Classify the orthomosaic ------------------------------------------------------------
    print("Classifying the orthomosaic...")
    is_water <- function(model, data) as.integer(predict(model, data, type = "class") == "water")
    water <- terra::predict(ortho, model, fun = is_water, na.rm = TRUE)

    # Cells under canopy taller than max_canopy_height cannot be water
    if (nzchar(chm_path)) {
        print(paste("Masking cells with canopy height above", max_canopy_height, "m..."))
        chm <- rast(chm_path)
        if (!same.crs(chm, ortho)) chm <- project(chm, ortho)
        chm <- resample(chm, ortho, method = "near")
        water <- ifel(!is.na(chm) & chm > max_canopy_height, 0, water)
    }

    # Remove water patches smaller than min_patch_area (m2)
    if (min_patch_area > 0) {
        patch_ids <- patches(water, directions = 8, zeroAsNA = TRUE)
        sizes <- freq(patch_ids)
        cell_area <- prod(res(water))
        small <- sizes$value[sizes$count * cell_area < min_patch_area]
        if (length(small) > 0) {
            print(paste("Removing", length(small), "water patches smaller than", min_patch_area, "m2..."))
            water <- ifel(patch_ids %in% small, 0, water)
        }
    }

    out_file <- file.path(out_folder, "surface_water.tif")
    writeRaster(water, out_file, datatype = "INT1U", overwrite = TRUE,
                names = "surface_water")
    water_cover <- global(water, "mean", na.rm = TRUE)[1, 1]
    print(paste0("Surface water covers ", round(100 * water_cover, 1), "% of the classified area"))
    print(paste("Surface water raster saved to:", out_file))
}

############################################################################################
# Water table and depth-to-water (DTW)
# Follows Chan, Dabros & McDermid (2026), Forests 17, 489 (section 2.4), after Rahman et al.
# (2017): the DTM is masked to surface water, the minimum water elevation in each grid cell is
# kriged into a water table surface, and DTW = DTM - water table (0 on surface water).
############################################################################################
dtw_map <- function(dtm_path, water_path, mask_path, mask_layer, grid_size, nmax, vgm_model,
                    kriging_res, out_folder) {
    library(terra)
    library(gstat)

    dir.create(out_folder, showWarnings = FALSE, recursive = TRUE)

    print("Reading input data...")
    dtm <- rast(dtm_path)[[1]]
    names(dtm) <- "dtm"
    water <- rast(water_path)[[1]]
    # Put the surface water raster on the DTM grid; "mode" keeps the majority class when the
    # water raster is finer than the DTM (e.g. a 2 cm orthomosaic classification)
    if (!compareGeom(water, dtm, stopOnError = FALSE)) {
        method <- if (res(water)[1] < res(dtm)[1]) "mode" else "near"
        print(paste0("Resampling the surface water raster to the DTM grid (", method, ")..."))
        water <- if (same.crs(water, dtm)) resample(water, dtm, method = method) else project(water, dtm, method = method)
    }
    is_water <- !is.na(water) & water == 1

    exclude <- NULL
    if (nzchar(mask_path)) {
        exclude <- if (nzchar(mask_layer)) vect(mask_path, layer = mask_layer) else vect(mask_path)
        if (!same.crs(exclude, dtm)) exclude <- project(exclude, dtm)
        print(paste("Excluding", nrow(exclude), "mask polygon(s) from the analysis..."))
    }

    # ---- Water elevations: minimum per grid cell, at the grid cell centre ---------------------
    water_elev <- mask(dtm, is_water, maskvalues = FALSE)
    if (!is.null(exclude)) water_elev <- mask(water_elev, exclude, inverse = TRUE)
    fact <- max(1, round(grid_size / res(dtm)[1]))
    grid_min <- aggregate(water_elev, fact = fact, fun = "min", na.rm = TRUE)
    pts <- as.points(grid_min, na.rm = TRUE)
    names(pts) <- "elev"
    obs <- data.frame(crds(pts), elev = pts$elev)
    print(paste("Water elevation points:", nrow(obs), "grid cells of", fact * res(dtm)[1], "m contain surface water"))
    if (nrow(obs) < 10) stop("Too few grid cells contain surface water to krige a water table (need at least 10).")
    writeVector(pts, file.path(out_folder, "water_points.gpkg"), overwrite = TRUE)

    # ---- Variogram and ordinary kriging -------------------------------------------------------
    print(paste("Fitting the", vgm_model, "variogram..."))
    sample_vgm <- variogram(elev ~ 1, locations = ~x + y, data = obs)
    fitted_vgm <- tryCatch(
        fit.variogram(sample_vgm, vgm(vgm_model)),
        error = function(e) stop("Variogram fit failed for model '", vgm_model, "': ", conditionMessage(e),
                                 ". Try another variogram model."))
    if (isTRUE(attr(fitted_vgm, "singular"))) {
        print("Warning! The variogram fit is singular; check the fitted parameters or try another model.")
    }
    print(fitted_vgm)
    write.csv(as.data.frame(fitted_vgm)[, c("model", "psill", "range", "kappa")],
              file.path(out_folder, "variogram_model.csv"), row.names = FALSE)

    png(file.path(out_folder, "variogram.png"), width = 1200, height = 900, res = 200)
    plot(sample_vgm$dist, sample_vgm$gamma, pch = 19, xlab = "Distance (m)", ylab = "Semivariance",
         main = paste("Water elevation variogram:", vgm_model), ylim = c(0, max(sample_vgm$gamma) * 1.1))
    lines(variogramLine(fitted_vgm, maxdist = max(sample_vgm$dist)), col = "blue", lwd = 2)
    dev.off()

    model <- gstat(formula = elev ~ 1, locations = ~x + y, data = obs, model = fitted_vgm, nmax = nmax)

    # Leave-one-out cross-validation of the water table at the water points
    cv <- gstat.cv(model, nfold = nrow(obs), verbose = FALSE, debug.level = 0)
    cv_stats <- data.frame(n_points = nrow(obs), mae = mean(abs(cv$residual)),
                           rmse = sqrt(mean(cv$residual^2)))
    write.csv(cv_stats, file.path(out_folder, "water_table_cv.csv"), row.names = FALSE)
    print(paste0("Water table leave-one-out cross-validation: MAE = ", round(cv_stats$mae, 3),
                 " m, RMSE = ", round(cv_stats$rmse, 3), " m"))

    target <- dtm
    if (kriging_res > res(dtm)[1]) {
        target <- aggregate(dtm, fact = round(kriging_res / res(dtm)[1]), fun = "mean", na.rm = TRUE)
        print(paste("Kriging on a", res(target)[1], "m grid, then resampling bilinearly to the DTM..."))
    } else {
        print(paste("Kriging on the DTM grid (", ncell(dtm), "cells)..."))
    }
    water_table <- interpolate(target, model, xyNames = c("x", "y"), index = 1, debug.level = 0)
    if (kriging_res > res(dtm)[1]) water_table <- resample(water_table, dtm, method = "bilinear")
    water_table <- mask(water_table, dtm)
    names(water_table) <- "water_table"

    # ---- DTW = DTM - water table; 0 on surface water and where the water table is above ground
    dtw <- dtm - water_table
    dtw <- ifel(dtw < 0, 0, dtw)
    dtw <- ifel(is_water, 0, dtw)
    if (!is.null(exclude)) {
        water_table <- mask(water_table, exclude, inverse = TRUE)
        dtw <- mask(dtw, exclude, inverse = TRUE)
    }
    names(dtw) <- "dtw"

    writeRaster(water_table, file.path(out_folder, "water_table.tif"), overwrite = TRUE)
    writeRaster(dtw, file.path(out_folder, "dtw.tif"), overwrite = TRUE)
    stats <- global(dtw, c("mean", "max"), na.rm = TRUE)
    print(paste0("DTW: mean = ", round(stats[1, "mean"], 3), " m, max = ", round(stats[1, "max"], 3), " m"))
    print(paste("Water table and DTW rasters saved to:", out_folder))
}
###############################################################################################################
normalized_lidar_knnidw <- function(in_las_folder, out_folder, rprocesses) {

    library(lidR)
    library(future)

    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    #read Las file and drop any noise from the point cloud
    ctg <- readLAScatalog(in_las_folder, filter = '-drop_class 7')
    opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/Normalized_PC/n_{*}")
    print("Normalize lidar data...")
    opt_progress(ctg) <- TRUE
    n_las <- normalize_height(ctg, algorithm = knnidw())
    # reset R mutilsession back to default
    plan(sequential)
}

##########################################################################
normalized_lidar_tin <- function(in_las_folder, out_folder, rprocesses) {

    library(lidR)
    library(future)

    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    #read Las file and drop any noise from the point cloud
    ctg <- readLAScatalog(in_las_folder, filter = '-drop_class 7')
    opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/n_{*}")
    print("Normalize lidar data...")
    opt_progress(ctg) <- TRUE

    n_las <- normalize_height(ctg, algorithm = tin())
    # reset R mutilsession back to default
    plan(sequential)
}

##########################################################################
normalized_lidar_kriging <- function(in_las_folder, out_folder, rprocesses) {

    library(lidR)
    library(future)

    plan(multisession, workers = rprocesses)
    set_lidr_threads(rprocesses)

    #read Las file and drop any noise from the point cloud
    ctg <- readLAScatalog(in_las_folder, filter = '-drop_class 7')
    opt_output_files(ctg) <- opt_output_files(ctg) <- paste0(out_folder, "/Normalized_PC/n_{*}")
    print("Normalize lidar data...")
    opt_progress(ctg) <- TRUE
    n_las <- normalize_height(ctg, algorithm = kriging())
    # reset R mutilsession back to default
    plan(sequential)
}

#########################################################################################
