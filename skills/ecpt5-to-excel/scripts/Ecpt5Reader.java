import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.io.*;
import java.util.*;
import java.util.zip.*;
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;
import com.db4o.*;
import com.db4o.ext.*;
import com.db4o.config.*;
import com.db4o.reflect.generic.*;

public class Ecpt5Reader {
  static ObjectContainer db;
  static String q(String s) {
    if(s==null) return "null";
    StringBuilder b=new StringBuilder("\"");
    for(char c:s.toCharArray()) {if(c=='"'||c=='\\') b.append('\\').append(c); else if(c<32) b.append(String.format("\\u%04x",(int)c)); else b.append(c);}
    return b.append('"').toString();
  }
  static String value(Object o, int depth) {
    if(o==null)return "null";
    if(o instanceof String || o instanceof Character)return q(o.toString());
    if(o instanceof Number || o instanceof Boolean){if(o instanceof Double && !Double.isFinite((Double)o))throw new IllegalArgumentException("NON_FINITE_NUMBER");return o.toString();}
    if(o instanceof GenericObject) return "{\"ref\":"+db.ext().getID(o)+"}";
    db.activate(o,3);
    if(depth>12)throw new IllegalArgumentException("COLLECTION_DEPTH_LIMIT");
    if(o instanceof Collection){List<String> a=new ArrayList<>();for(Object x:(Collection)o)a.add(value(x,depth+1));return "["+String.join(",",a)+"]";}
    if(o instanceof Map){List<String> a=new ArrayList<>();for(Object x:((Map)o).entrySet()){Map.Entry e=(Map.Entry)x;a.add("["+value(e.getKey(),depth+1)+","+value(e.getValue(),depth+1)+"]");}return "{\"map\":["+String.join(",",a)+"]}";}
    if(o.getClass().isArray()){List<String>a=new ArrayList<>();for(int i=0;i<java.lang.reflect.Array.getLength(o);i++)a.add(value(java.lang.reflect.Array.get(o,i),depth+1));return "["+String.join(",",a)+"]";}
    return q(o.toString());
  }
  static void dump(Path f, Path target) throws Exception {
    Configuration cfg=Db4o.newConfiguration();cfg.readOnly(true);cfg.activationDepth(3);cfg.callbacks(false);cfg.exceptionsOnNotStorable(false);
    db=Db4o.openFile(cfg,f.toString());
    Set<Long> done=new HashSet<>(); int count=0;
    try(BufferedWriter out=Files.newBufferedWriter(target,StandardCharsets.UTF_8)) {
      for(StoredClass sc:db.ext().storedClasses()) {
        if(!sc.getName().startsWith("com.toone."))continue;
        for(long id:sc.getIDs()) {
          if(!done.add(id))continue;
          Object o=db.ext().getByID(id);db.activate(o,3);
          String type=db.ext().reflector().forObject(o).getName();
          List<String> fields=new ArrayList<>();Set<String> names=new HashSet<>();
          StoredClass cls=db.ext().storedClass(o);
          while(cls!=null){for(StoredField sf:cls.getStoredFields()){if(names.add(sf.getName())){Object v=sf.get(o);fields.add(q(sf.getName())+":"+value(v,0));}}cls=cls.getParentStoredClass();}
          out.write("{\"id\":"+id+",\"type\":"+q(type)+",\"fields\":{"+String.join(",",fields)+"}}\n");count++;
        }
      }
    } finally {db.close();}
    System.out.println(f.getFileName()+" objects="+count);
  }
  public static void main(String[] args)throws Exception {
    if(args[0].equals("arr")) {
      try(ZipFile z=new ZipFile(args[1]);InputStream in=z.getInputStream(z.getEntry("arr"))) {
        byte[] b=in.readAllBytes();
        if(!(b.length>5 && b[0]=='<' && b[1]=='?')) {
          Cipher c=Cipher.getInstance("DES/ECB/PKCS5Padding");
          c.init(Cipher.DECRYPT_MODE,new SecretKeySpec(new byte[]{-56,31,7,82,112,117,-50,-20},"DES"));b=c.doFinal(b);
        }
        Files.write(Paths.get(args[2]),b);
      }
    } else if(args[0].equals("dump")) dump(Paths.get(args[1]),Paths.get(args[2]));
    else throw new IllegalArgumentException("Expected arr or dump");
  }
}
