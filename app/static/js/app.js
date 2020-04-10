{/* <script>

  $(function(){
    // Ajax button click
    $('.card').on('click',function(){
      $.ajax({
        url:'/employee',
        type:'get',
        data:{
          'id':$(this).data('id')
        }
      })
      // Ajaxリクエストが成功した時発動
      .done( (data) => {
        $('.result').html(data);
        console.log(data);
      })
      // Ajaxリクエストが失敗した時発動
      .fail( (data) => {
        $('.result').html(data);
        console.log(data);
      })
      // Ajaxリクエストが成功・失敗どちらでも発動
      .always( (data) => {

      });
    });
  });
</script> */}