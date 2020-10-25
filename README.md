# Leetcode-Nvim Conquer the Leetcode problems in nvim

![Leetcode in vim](demo.gif)

## <a id="introduction"></a>Introduction

This a very simple plugin that makes you can write leetcode solutions in your beloved nvim editor.
Login with browser cookies and happy coding.

## <a id="installing"></a>Installing

This plugin is written in python3 and you need to install requests.
```
pip install requests
```

Use Plug-Vim

```Bash
Plug 'youkabeng/leetcode-nvim'
```

After that, run "UpdateRemotePlugins" command once in nvim.

```
:UpdateRemotePlugins
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
```

4. Test your code with test function

```
call LCTest()
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



