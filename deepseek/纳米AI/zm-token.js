const userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0';
    const a: string[] = [
        "Web",
        date.toISOString().replace('Z', '+08:00'),
        "1.2",
        nData.mid,
        md5(userAgent)
    ];
 zm-token =  md5(a.join(""))