SELECT [pipe_line_id], [item_line], pl.[shared],[date],[note]
FROM    [dbo].[pipe_line_item] pi
LEFT JOIN [dbo].[pipe_line] pl ON pi.pipe_line_id = pl.id
WHERE [shared] = 'Shared'