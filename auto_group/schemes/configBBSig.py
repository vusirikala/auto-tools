schemeType = "PKSIG"
short = "public-keys"

keygenFuncName 	= "keygen"
signFuncName 	= "sign"
verifyFuncName 	= "verify"

masterPubVars = ["pk"]
masterSecVars = ["sk"]

keygenPubVar = "pk"
keygenSecVar = "sk"
messageVar = "m" 
signatureVar = "sig" 
functionOrder = [keygenFuncName, signFuncName, verifyFuncName]
