SELECT pl.[id]
      ,pl.[shared]
      ,pl.[division]
      ,pl.[entity]
      ,pl.[region]
      ,pl.[owner]
      ,pl.[product]
      ,pl.[product_type]
      ,pl.[customer]
      ,pl.[contact]
      ,pl.[customer_prospect]
      ,pl.[model]
      ,pl.[project]
      ,pl.[status]
      ,pl.[priority]
      ,pl.[refrigerant]
      ,pl.[application]
      ,pl.[system_models]
      ,pl.[target_spec]
      ,pl.[comp_model]
      ,pl.[scope]
      ,pl.[resolved]
      ,pl.[contact]
      ,pl.[remark]
    --   ,pl.[delete_flag]
      ,pl.[created_date]
      ,pl.[updated_date]
      ,pli.date AS LatestNoteDate
    --   ,pli.follow_up AS FollowUp
      ,pli.note AS LatestNote


FROM
    [dbo].[pipe_line] pl
LEFT JOIN (
    SELECT
        pipe_line_id,
        date,
        note,
        ROW_NUMBER() OVER (PARTITION BY pipe_line_id ORDER BY date DESC) AS rn
    FROM
        [dbo].[pipe_line_item]
) pli ON pl.id = pli.pipe_line_id AND pli.rn = 1

WHERE (pl.delete_flag=0 or pl.delete_flag IS NULL) and pl.[shared]='Shared';