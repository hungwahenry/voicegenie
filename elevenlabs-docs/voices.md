List voices
Gets a list of all available voices for a user with search, filtering and pagination.
GET
/v2/voices

cURL

curl https://api.elevenlabs.io/v2/voices \
 -H "xi-api-key: xi-api-key"
Headers
xi-api-key
string
Required
Query parameters
next_page_token
string or null
Optional
The next page token to use for pagination. Returned from the previous request. Use this in combination with the has_more flag for reliable pagination.

page_size
integer
Optional
Defaults to 10
How many voices to return at maximum. Can not exceed 100, defaults to 10. Page 0 may include more voices due to default voices being included.
search
string or null
Optional
Search term to filter voices by. Searches in name, description, labels, category.
sort
string or null
Optional
Which field to sort by, one of ‘created_at_unix’ or ‘name’. ‘created_at_unix’ may not be available for older voices.

sort_direction
string or null
Optional
Which direction to sort the voices in. 'asc' or 'desc'.
voice_type
string or null
Optional
Type of the voice to filter by. One of ‘personal’, ‘community’, ‘default’, ‘workspace’, ‘non-default’, ‘saved’. ‘non-default’ is equal to all but ‘default’. ‘saved’ is equal to non-default, but includes default voices if they have been added to a collection.

category
string or null
Optional
Category of the voice to filter by. One of 'premade', 'cloned', 'generated', 'professional'
fine_tuning_state
string or null
Optional
State of the voice’s fine tuning to filter by. Applicable only to professional voices clones. One of ‘draft’, ‘not_verified’, ‘not_started’, ‘queued’, ‘fine_tuning’, ‘fine_tuned’, ‘failed’, ‘delayed’

collection_id
string or null
Optional
Collection ID to filter voices by.
include_total_count
boolean
Optional
Defaults to true
Whether to include the total count of voices found in the response. NOTE: The total_count value is a live snapshot and may change between requests as users create, modify, or delete voices. For pagination, rely on the has_more flag instead. Only enable this when you actually need the total count (e.g., for display purposes), as it incurs a performance cost.

voice_ids
list of strings or null
Optional
Voice IDs to lookup by. Maximum 100 voice IDs.
Response
Successful Response
voices
list of objects
The list of voices matching the query.

Show 22 properties
has_more
boolean
Indicates whether there are more voices available in subsequent pages. Use this flag (and next_page_token) for reliable pagination instead of relying on total_count.

total_count
integer
The total count of voices matching the query. This value is a live snapshot that reflects the current state of the database and may change between requests as users create, modify, or delete voices. For reliable pagination, use the has_more flag instead of relying on this value. Only request this field when you actually need the total count (e.g., for display purposes), as calculating it incurs a performance cost.

next_page_token
string or null
Token to retrieve the next page of results. Pass this value to the next request to continue pagination. Null if there are no more results.
Errors

422
Unprocessable Entity Error
