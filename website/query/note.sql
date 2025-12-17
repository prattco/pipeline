-- note.sql

SELECT 
    [note_p].[id],
    [user_p].[email],
    [user_p].[company_name],
    [note_p].[data],
    [note_p].[date],
    [note_p].[user_id],
    [reply_user].[email] AS [reply_user_email],
    [note_reply].[id] AS [reply_id],
    [note_reply].[data] AS [reply_data],
    [note_reply].[date] AS [reply_date],
    [note_reply].[user_id] AS [reply_user_id]
FROM [note_p]  -- CHANGED: note -> note_p
LEFT JOIN [note_p] AS [note_reply] ON [note_p].[id] = [note_reply].[ref_id] -- CHANGED: note -> note_p
LEFT JOIN [user_p] ON [note_p].[user_id] = [user_p].[id] -- CHANGED: user -> user_p
LEFT JOIN [user_p] AS [reply_user] ON [note_reply].[user_id] = [reply_user].[id] -- CHANGED: user -> user_p
WHERE [note_p].[ref_id] IS NULL;