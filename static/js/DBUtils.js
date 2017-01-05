var DBUtils = {};

DBUtils.GetDefaultValue = function (sqlType) {
    var uppercaseSqlType = sqlType.toUpperCase();
    if (uppercaseSqlType.startsWith("NVARCHAR") || uppercaseSqlType.startsWith("VARCHAR"))
    {
        return "";
    }
    else if (uppercaseSqlType.startsWith("NUMBER") || uppercaseSqlType.startsWith("INT")) {
        return 0;
    }
    else if (uppercaseSqlType.startsWith("FLOAT") || uppercaseSqlType.startsWith("DECIMAL") ){
        return 0.0;
    }
    else if (uppercaseSqlType.startsWith("TIME") || uppercaseSqlType.startsWith("DATE")) {
        return new Date();
    }
    else {
        console.log("UNEXPECTED SQL TYPE: " + uppercaseSqlType);
    }
};

DBUtils.CloneEntity = function (origEntity) {

}