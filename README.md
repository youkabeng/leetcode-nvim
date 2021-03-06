# Leetcode-Nvim Conquer the Leetcode problems in nvim

![Leetcode in vim](https://github.com/youkabeng/leetcode-nvim/raw/master/demo.gif)

## <a id="introduction"></a>Introduction

This a very simple plugin that makes you can write leetcode solutions in your beloved nvim editor.
Login with browser cookies and happy coding.

## <a id="installing"></a>Installing

This plugin is written in python3 and you need to install some packages.
```
pip install pynvim requests beautifulsoup4 playsound
```

Use Plug-Vim

```Bash
Plug 'youkabeng/leetcode-nvim'
```

After that, run "UpdateRemotePlugins" command once in nvim.

```
:UpdateRemotePlugins
```

## <a if="config"></a>Config

Set default lang in your vim config file

```
let g:leetcode_default_lang = 'c'
```

Available languages are as follows:

|Language|Abbreviation|
|--------|------------|
|C++|cpp|
|Java|java|
|Python 2|python|
|Python 3|python3|
|C|c|
|C#|csharp|
|Javascript|javascript|
|Ruby|ruby|
|Swift|swift|
|Go|golang|
|Scala|scala|
|Kotlin|kotlin|
|Rust|rust|
|PHP|php|
|Typescript|typescript|

(Optional) Give a repo path(absolute path only), every accepted solution will be copied to the repo.    
You can use github to keep track of your progress.

```
let g:leetcode_repo_path = '/your/repo/path'
```

(Optional) Add something interesting to this small plugin.    
You can specify two sound files(wav and mp3 supported) to enable some sound effect.    
The send_ringtone will be played every time the command is sent.    
The pass_ringtone will be played when your answer is accepted.    

**YOUR EVERY SUBMIT COUNTS AND ENJOY EVOLVING!**

But please be noted, the volume can't be setup separately for now.

```
let g:leetcode_pass_ringtone = '/your/sound/ringtone/xx.mp3'
let g:leetcode_send_ringtone = '/your/sound/ringtone/yy.mp3'
```

(Optional) Shortcuts

Feel free to change key bindings.

```
noremap <Leader>lcl :call LCListProblems()<CR>
noremap <Leader>lcc :call LCCoding()<CR>
noremap <Leader>lct :call LCTest()<CR>
noremap <Leader>lcs :call LCSubmit()<CR>
noremap <Leader>lcg :call LCGetLatestSubmission()<CR>
noremap <Leader>lcr :call LCCodingReset()<CR>
```


## <a id="usage"></a>Usage

1. First use browser cookie to log in. Only 'us' is supported for now.

Copy "csrftoken" and "leetcode_session"

```
call LCLoginWithCookie('us', 'csrftoken', 'leetcode_session')
```

2. Get all problem titles

```
call LCListProblems()
```

3. Move the cursor to the problem you want to challenge and call next function

```
call LCCoding()
call LCCoding('cpp')
```

4. Test your code with test function.

You can input your testcase as a parameter.

Use '//n//' to represent '\n'

```
call LCTest()
call LCTest('"abcbc"')
```

5. Retrieve latest submission

```
call LCGetLatestSubmission()
```

6. Reset code

```
call LCCodingReset()
```

7. Submit
```
call LCSubmit()
```
