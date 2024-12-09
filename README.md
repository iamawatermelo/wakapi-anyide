# wakapi-anyide
Log your coding time against any WakaTime-like server.

> [!NOTE]
> Teenager? Check out [High Seas](https://highseas.hackclub.com/)!

> [!IMPORTANT]
> wakapi-anyide is still in development.
> Please report any tracking bugs!

## Alternatives

You should try use an [editor extension](https://wakatime.com/plugins) over wakapi-anyide if you can.
If you don't need precise coding metrics, use the [WakaTime app](https://wakatime.com/linux) instead. The WakaTime app does not work with High Seas.

## Quickstart guide for most IDEs
These instructions are best run in an existing project.

- Create a `.wakatime.cfg` file if you don't already have one.
  If you're doing High Seas, this is explained in the Signpost (click "View instructions for all platforms" and scroll down).

- **Set your IDE to autosave as quickly as possible.**
  This is how wakapi-anyide is able to track your coding time. Ideally, something like a second, so it saves as you type.
  However, anything under your editor timeout preference in your WakaTime settings is fine.
  For High Seas, it **must** be under two minutes.

- Install `wakapi-anyide` with your favourite Python package manager (try `pipx install wakapi-anyide[color]` to install with colour support!)

- Run `wakapi-anyide setup` and follow the instructions.  
  The **included paths** are the paths that wakapi-anyide will watch for changes.  
  The **excluded paths** are the paths that wakapi-anyide will ignore.
  You should put things like generated/compiled code or packages there (ie `*.o`, `/node_modules`).
  By default, if you have a `.gitignore` then it will ignore every file listed in it.

- Inspect and edit the generated `wak.toml`:
  ```toml
  # https://github.com/iamawatermelo/wakapi-anyide v0.6.6
  
  [meta]
  version = 1
  watchers = ['files']
  
  [files]
  include = ["*"]  # files to include in tracking
  exclude = []  # files to exclude in tracking
  exclude_files = [".gitignore"]  # files whose contents will be used to exclude other files from tracking
  exclude_binary_files = true  # whether to ignore binary files
  # language_mapping = {".kicad_sch" = "Kicad Schematic"}  # custom language mapping
  # editor_mapping = {".kicad_sch" = "Kicad Schematic Editor"} # custom editor mapping
  large_file_threshold = "64KiB" # files larger than this will not do precise line diffing, it will only count total lines. 
  # Make sure to capture all relavant groups that would be part of the original file. Don't include the extension in the captures though, the extension is already determined.
  # Also make sure to double escape, TOML uses backslashes for line breaks already
  autosave_masking = {".kicad_sch" = {"regex" = "(^.*)(?:\\.kicad_sch-bak)", folder = ""}}

  [project]
  name = "PROJECT NAME"  # your project name
  ```

- Run `wakapi-anyide test` in the same directory you have `wak.toml` in.
  Ensure that wakapi-anyide is not tracking any generated files by reading through the paths it has cached.
  If there are no generated files in the cached paths, you're good to go.

- Run `wakapi-anyide track` to actually track your progress.
  You must run this every time.

## What wakapi-anyide sends

wakapi-anyide tells the WakaTime server:

- your OS and that you are using wakapi-anyide (`wakatime/unset (Linux-none-none) wakapi-anyide-wakatime/unset`)
- your editor (if specified), default is wakapi-anyide
- an anonymised hostname based off of your computer's name (`anonymised machine 749f8c4e`), or specified hostname
- the relative path of the files you change (`./wakatime_anyide/__init__.py`)
- the estimated time you have spent
- your estimated cursor position over time
- the estimated or specified language of any files you edit (`py`, `Makefile`)
- the amount of lines changed
- the branch you are editing if you use Git (WIP)
- any information you specified in the project section of `wak.toml`

Additionally, the WakaTime server will be able to see:

- your IP address, which means your approximate location
- the time of day your requests are being sent

Every website you visit can see this information.

wakapi-anyide does not send:

- any information about your system not listed above, like your username
- file content
- filenames outside of those included in your `wak.toml`

For security, wakapi-anyide does not use wakatime-cli.

## Support for existing WakaTime configuration

wakapi-anyide supports the `WAKATIME_HOME` and the `WAKATIME_API_KEY` environment variables.
The configuration value takes precedence over the environment variable.

### $WAKATIME_HOME/.wakatime.cfg

Only these configuration values are supported:

#### [settings]

| option                        | description                                                                                          | type     | default value                     |
| ----------------------------- | ---------------------------------------------------------------------------------------------------- | -------- | --------------------------------- |
| api_key                       | Your WakaTime API key.                                                                               | _string_ |                                   |
| api_key_vault_cmd             | A command to get your api key. Shell syntax is not supported, use `sh -c "<your command>"` for that. | _string_ |                                   |
| api_url                       | The WakaTime API base url.                                                                           | _string_ | <https://api.wakatime.com/api/v1> |
| hostname                      | Optional name of local machine.                                                                      | _string_ | (an anonymised hostname)          |
| heartbeat_rate_limit_seconds  | How often to send heartbeats, in seconds.                                                            | _int_    | 120                               |

All other configuration values are silently ignored.

### .wakatime-project

Not supported.

## Quirks and limitations

### Tracking

wakapi-anyide is not integrated with your editor. It can only guess what you are doing through file changes.
As such, it may sometimes pick up generated files.
A useful feature of wakapi-anyide is that you can specify what editor and what language you are working on, based on the file extension.

### Binary files

wakapi-anyide can track binary files with `files.exclude_binary_files = false`.
File changes are reported specially:
- they are appended with `#wakapi-anyide-binary` in tracking
- cursor position is set to the last change in the binary file
- the line count is set to the binary diff count unless the file is larger than the threshold

### Large or numerous files

For performance reasons, files which are larger than the specified threshold (default is 64KiB) will only report changes in *total* file line count or file size in bytes if its binary. It does not know the number of lines that are modified, but it can tell that the file changed based on checksum. This will still be fine for High Seas, since only the total line count matters. If you have thousands of files it is recommended to set the threshold to 0, because every specified file in your project is stored in RAM.